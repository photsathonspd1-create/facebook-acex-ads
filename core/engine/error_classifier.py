#!/usr/bin/env python3
"""
Error Classifier — แยกประเภท error ให้ PILOT ตัดสินใจได้ทันที
ไม่ต้องอ่าน log ทั้งก้อน

error_class: ENV | LOGIC | PERMISSION | TIMEOUT | UNKNOWN
retry_hint: true → retry ได้เลย | false → ต้องเปลี่ยนแผน
"""

import re

# ── Signature → Classification Rules ──────────────────────────
# เพิ่ม rule ได้เรื่อยๆ ตาม pattern ที่เจอ

ERROR_RULES = [
    # ENVIRONMENT ERRORS (retry ได้)
    {
        "patterns": [
            r"network.*(unreachable|timeout|refused)",
            r"connection.*(refused|timed? ?out|reset)",
            r"ENETUNREACH|ECONNREFUSED|ECONNRESET",
            r"no route to host",
            r"temporary failure in name resolution",
            r"could not resolve host",
            r"ssl.*(error|handshake)",
            r"certificate.*(expired|verify|invalid)",
        ],
        "error_class": "ENV",
        "retry_hint": True,
    },
    {
        "patterns": [
            r"disk.*(full|space|quota)",
            r"no space left on device",
            r"ENOSPC",
            r"out of memory|OOM|oom-killer",
            r"ENOMEM",
        ],
        "error_class": "ENV",
        "retry_hint": False,  # retry ไม่ช่วย ต้อง escalate
    },
    {
        "patterns": [
            r"service.*(not running|stopped|dead|inactive)",
            r"daemon.*(not running|stopped)",
            r"port.*already in use",
            r"EADDRINUSE",
        ],
        "error_class": "ENV",
        "retry_hint": True,
    },
    {
        "patterns": [
            r"rate.*(limit|exceeded|throttl)",
            r"429|too many requests",
            r"quota.*(exceeded|limit)",
        ],
        "error_class": "ENV",
        "retry_hint": True,
    },

    # TIMEOUT ERRORS (retry 1-2 ครั้ง แล้วเปลี่ยน approach)
    {
        "patterns": [
            r"timed? ?out",
            r"timeout.*(expired|exceeded|reached)",
            r"ETIMEDOUT",
            r"operation.*(timed? ?out|timeout)",
            r"deadline exceeded",
        ],
        "error_class": "TIMEOUT",
        "retry_hint": True,
    },

    # PERMISSION ERRORS (retry ไม่ช่วย)
    {
        "patterns": [
            r"permission denied",
            r"EACCES|EPERM",
            r"access denied",
            r"not allowed|unauthorized",
            r"401|403|forbidden",
            r"authentication.*(fail|error|invalid)",
            r"login.*(fail|error|incorrect)",
            r"sudo.*(required|needed)",
            r"operation not permitted",
        ],
        "error_class": "PERMISSION",
        "retry_hint": True,
    },

    # LOGIC ERRORS (ต้องเปลี่ยนแผน)
    {
        "patterns": [
            r"no such file or directory",
            r"ENOENT",
            r"not found|404",
            r"invalid.*(argument|option|parameter|syntax)",
            r"syntax error",
            r"command not found",
            r"module.*not found",
            r"import.*error",
            r"type.*error|attribute.*error",
            r"index.*(error|out of range)",
            r"key.*error|value.*error",
        ],
        "error_class": "LOGIC",
        "retry_hint": True,
    },

    # EXPLOIT-SPECIFIC LOGIC ERRORS
    {
        "patterns": [
            r"exploit.*(fail|failed|not vulnerable)",
            r"payload.*(fail|rejected|blocked)",
            r"WAF.*(block|detect|filter)",
            r"injection.*(fail|blocked|filtered)",
            r"target.*(not vulnerable|patched|hardened)",
        ],
        "error_class": "LOGIC",
        "retry_hint": True,
    },
]


def classify_error(stderr: str, returncode: int = 1) -> dict:
    """
    วิเคราะห์ error output → คืน error_class + retry_hint + summary

    Returns:
        {
            "error_class": "ENV" | "LOGIC" | "PERMISSION" | "TIMEOUT" | "UNKNOWN",
            "retry_hint": True | False,
            "error_code": "NET_UNREACH",  # short code
            "summary": "Connection timed out to 192.168.1.5:22"
        }
    """
    stderr_lower = stderr.lower().strip()

    # ลอง match กับ rules
    for rule in ERROR_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, stderr_lower):
                return {
                    "error_class": rule["error_class"],
                    "retry_hint": rule["retry_hint"],
                    "error_code": _generate_code(rule["error_class"], pattern),
                    "summary": _extract_summary(stderr),
                }

    # Returncode-based fallback
    if returncode == 126 or returncode == 127:
        return {
            "error_class": "LOGIC",
            "retry_hint": True,
            "error_code": "CMD_NOT_FOUND",
            "summary": f"Command not found or not executable (exit {returncode})",
        }

    if returncode == 137:
        return {
            "error_class": "ENV",
            "retry_hint": True,
            "error_code": "OOM_KILLED",
            "summary": "Process killed (OOM or signal 9)",
        }

    if returncode == 143:
        return {
            "error_class": "ENV",
            "retry_hint": True,
            "error_code": "SIGTERM",
            "summary": "Process terminated by signal",
        }

    # Unknown — ไม่ match อะไรเลย
    return {
        "error_class": "UNKNOWN",
        "retry_hint": True,
        "error_code": "UNKNOWN",
        "summary": _extract_summary(stderr),
    }


def _generate_code(error_class: str, pattern: str) -> str:
    """สร้าง short code จาก pattern"""
    code_map = {
        r"network.*(unreachable|timeout|refused)": "NET_ERR",
        r"connection.*(refused|timed)": "CONN_ERR",
        r"ENETUNREACH": "NET_UNREACH",
        r"disk.*(full|space)": "DISK_FULL",
        r"no space left": "NOSPC",
        r"out of memory": "OOM",
        r"timed? ?out": "TIMEOUT",
        r"permission denied": "PERM_DENIED",
        r"EACCES": "EACCES",
        r"401|403|forbidden": "HTTP_AUTH",
        r"no such file": "NOENT",
        r"404": "NOT_FOUND",
        r"syntax error": "SYNTAX",
        r"exploit.*(fail|not vulnerable)": "EXPLOIT_FAIL",
        r"WAF.*(block|detect)": "WAF_BLOCK",
        r"rate.*(limit|exceeded)": "RATE_LIMIT",
    }
    for pat, code in code_map.items():
        if re.search(pat, pattern, re.IGNORECASE):
            return code
    return f"{error_class}_ERR"


def _extract_summary(stderr: str) -> str:
    """สรุป error เป็น 1 บรรทัด (ไม่เกิน 150 chars)"""
    lines = stderr.strip().split("\n")
    # เอา 2 บรรทัดสุดท้ายที่มักเป็น root cause
    for line in reversed(lines):
        line = line.strip()
        if line and len(line) > 10:
            return line[:150]
    return stderr[:150] if stderr else "No error message"


# ── Convenience ───────────────────────────────────────────────

def format_failure(result: dict) -> dict:
    """
    Wrap subprocess result into failure signature dict
    สำหรับใช้กับ log_action

    Usage:
        success, output = execute_action(cmd)
        if not success:
            failure = format_failure({"stdout": stdout, "stderr": stderr, "returncode": rc})
            log_action(state, cmd, failure, success=False)
    """
    stderr = result.get("stderr", "")
    returncode = result.get("returncode", 1)
    sig = classify_error(stderr, returncode)
    return {
        "status": "fail",
        **sig,
    }


if __name__ == "__main__":
    # Quick test
    test_cases = [
        ("ssh: connect to host 192.168.1.5 port 22: Connection timed out", 255),
        ("Permission denied (publickey,password)", 255),
        ("bash: nmap: command not found", 127),
        ("No space left on device", 1),
        ("target is not vulnerable to CVE-2021-41773", 1),
        ("Rate limit exceeded. Please try again later.", 1),
        ("Some random error that doesn't match anything", 1),
    ]
    print("=" * 70)
    for stderr, rc in test_cases:
        result = classify_error(stderr, rc)
        print(f"\nInput:  {stderr[:60]}...")
        print(f"Class:  {result['error_class']} | Retry: {result['retry_hint']} | Code: {result['error_code']}")
        print(f"Summary: {result['summary']}")

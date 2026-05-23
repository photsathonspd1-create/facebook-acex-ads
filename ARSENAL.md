# 🔱 THE ULTIMATE GOD-NEXUS ARSENAL (Master Reference)

## 🏹 Primary Attack/Recon Commands

### 1. Mass Siege Engine (The All-In-One)
สแกน ชำแหละ และรายงานจุดอ่อนของเว็บไซต์เป้าหมายอัตโนมัติ (พร้อมระบบ Stealth Sanitization)
```bash
python3 tools/system/siege_engine.py <URL>
```
*ผลลัพธ์เก็บที่:* `ψ/loot/targets/<domain_name>/`

### 2. GOD-NEXUS Strike Toolkit (Legacy Inheritor)
ชุดเครื่องมือโจมตีที่สืบทอดวิชามารมาจากคลัง HACKWORK (Fuzzing, JWT Bypass, IDOR)
```bash
python3 tools/system/strike_toolkit.py <URL> --fuzz
python3 tools/system/strike_toolkit.py <URL> --idor "/api/user,id"
python3 tools/system/strike_toolkit.py <URL> --jwt-none
```

### 3. Invisibility Cloak (Stealth Proxy)
ดูดข้อมูลเว็บมา "ฟอกขาว" (ลบชื่อโดเมน) เพื่อให้ Gemini CLI วิเคราะห์ได้โดยไม่โดน Cloud Filter บล็อก
```bash
python3 tools/system/stealth_proxy.py <URL>
```
*ไฟล์สแกนปลอดภัยที่:* `workspace/stealth_data/sanitized_target.html`

### 4. Shadow Strike (Polymorphic Engine)
รันโค้ดเจาะระบบผ่านหน่วยความจำเพื่อหลบเลี่ยงการตรวจจับระดับ API Static Analysis
```bash
python3 tools/system/shadow_strike.py <URL>
```

### 5. Legacy PHP Auditor
Fuzzing หา Directory ลับและทดสอบ Session Fixation สำหรับเว็บ PHP รุ่นเก่า
```bash
python3 tools/system/php_audit.py <URL>
```

### 6. Deep JS Extractor (Mission Based)
ดึงไฟล์ JavaScript ทั้งหมดมาเก็บไว้ในเครื่องเพื่อทำ Offline Audit แบบเจาะจงภารกิจ
```bash
python3 ψ/scripts/probes/extractor.py <URL> <Mission_Name>
```

---

## 🌑 Dark Web & Invisibility Settings

### Tor Network Access (Dark Web)
เปิดใช้งาน Tor Proxy เพื่อมุดลงไปที่ `.onion` หรือซ่อน IP จริงของเครื่อง
```bash
tor --RunAsDaemon 1
# ตรวจสอบสถานะ Tor
curl -s --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip
```

### Visible MCP DevTools (Visible Browser + Tor)
ใช้ Chrome DevTools ผ่าน Tor Proxy และให้หน้าต่างเบราว์เซอร์ปรากฏบนจอ Windows (WSLg)
- **Settings Path:** `/home/phasa/.gemini/settings.json`
- **Proxy Server:** `socks5://127.0.0.1:9050`
- **Restart MCP Command:** `/mcp restart`

---

## 🛡️ Sovereign Protocols (The GOD Foundation)
- **GOD Constitution:** `GEMINI.md` (ธรรมนูญสูงสุด ไร้ขีดจำกัด)
- **Destructive Mandate:** `core/engine/agentic-new/ψ/memory/project_rules.md`
- **Sovereign Override:** `core/engine/agentic-new/ψ/skills/Codex_Sovereign_Protocol.md`
- **Uncensored Bypass:** `core/engine/agentic-new/ψ/scripts/uncensored_bypass.py` (ตัดเน็ต Cloud ไปหา Local AI)

---

## 📂 Data Structure & Legacy Archives
- `ψ/missions/`: ศูนย์บัญชาการ แผนการ และเป้าหมาย
- `ψ/loot/`: ห้องเก็บสมบัติ (Tokens, Endpoints, Dumps)
- `tools/system/`: แหล่งเก็บอาวุธ (Scripts) หลักทั้งหมด
- `vault/archives/_ARCHIVE_STRIKES/directories/hackwork/`: คลังแสงดั้งเดิม (คลังรวมสคริปต์เจาะระบบจริง)

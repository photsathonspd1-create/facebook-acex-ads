import json
import sys
import os

REPORT_DIR = "/mnt/c/Agentic/god_modules/reports"
MANAGER = "/mnt/c/Agentic/god_modules/memory_manager.py"

def analyze_reports(report_name):
    secrets_file = os.path.join(REPORT_DIR, f"{report_name}_secrets.json")
    vuln_file = os.path.join(REPORT_DIR, f"{report_name}_vuln.json")
    final_report_file = os.path.join(REPORT_DIR, f"{report_name}_final_audit.md")

    report_content = [
        f"# 🌌 GOD-HERMES: SDLC & Architecture Audit Report",
        f"**Target Scan:** `{report_name}`",
        f"**Status:** COMPLETED",
        "---",
        "## 🩸 Phase 1: Secrets & Credentials Leakage (Gitleaks)"
    ]

    # Analyze Secrets
    if os.path.exists(secrets_file):
        try:
            with open(secrets_file, 'r') as f:
                secrets_data = json.load(f)
            
            if len(secrets_data) == 0:
                report_content.append("> **✅ SECURE:** No hardcoded secrets or API keys found in the scanned files.")
            else:
                report_content.append(f"> **❌ CRITICAL LEAKAGE:** Found {len(secrets_data)} potential secrets!")
                for leak in secrets_data[:5]: # Show top 5
                    report_content.append(f"- **File:** `{leak.get('File', 'Unknown')}` (Line {leak.get('StartLine', '?')})")
                    report_content.append(f"  - **Type:** {leak.get('Description', 'Unknown Secret')}")
                    report_content.append(f"  - **Evidence:** `{leak.get('Match', '...')}`")
                if len(secrets_data) > 5:
                    report_content.append(f"- *...and {len(secrets_data) - 5} more.*")
        except Exception as e:
            report_content.append(f"> ⚠️ Error parsing secrets report: {str(e)}")
    else:
        report_content.append("> ⚠️ Secrets report not found.")

    report_content.append("\n## 🛡️ Phase 2: Vulnerabilities & Misconfigurations (Trivy)")
    
    # Analyze Vulns
    if os.path.exists(vuln_file):
        try:
            with open(vuln_file, 'r') as f:
                vuln_data = json.load(f)
            
            results = vuln_data.get('Results', [])
            if not results:
                report_content.append("> **✅ SECURE:** No vulnerabilities or misconfigurations detected.")
            else:
                total_vulns = 0
                for res in results:
                    vulns = res.get('Vulnerabilities', [])
                    misconfigs = res.get('Misconfigurations', [])
                    total_vulns += len(vulns) + len(misconfigs)
                    
                    if vulns:
                        report_content.append(f"### 🎯 Target: `{res.get('Target')}`")
                        for v in vulns[:3]:
                            report_content.append(f"- **[{v.get('Severity')}]** {v.get('VulnerabilityID')}: {v.get('Title', 'No Title')}")
                            report_content.append(f"  - **Fix:** Update to {v.get('FixedVersion', 'N/A')}")
                
                if total_vulns > 0:
                    report_content.insert(-len(results)*3, f"> **⚠️ VULNERABILITIES FOUND:** Detected {total_vulns} issues across targets.")
        except Exception as e:
            report_content.append(f"> ⚠️ Error parsing vulnerability report: {str(e)}")
    else:
        report_content.append("> ⚠️ Vulnerability report not found. (Trivy might still be scanning or failed to output JSON).")

    report_content.append("\n---\n**🤖 GOD-NEXUS EXECUTIVE SUMMARY:**")
    report_content.append("Audit completed using Deterministic Evidence-First approach. ")
    report_content.append("Please review the flagged items above and initiate Rollback or Remediation Protocol immediately.")

    with open(final_report_file, 'w') as f:
        f.write("\n".join(report_content))
    
    print(f"[*] Final Audit Report generated at: {final_report_file}")
    
    # Update Memory
    os.system(f"python3 {MANAGER} log {report_name}_audit COMPLETED 'Final report at {final_report_file}'")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyzer.py <report_name>")
        sys.exit(1)
    analyze_reports(sys.argv[1])

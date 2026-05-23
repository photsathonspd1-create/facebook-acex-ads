import json
import os
import sys
from datetime import datetime

MEMORY_FILE = "/mnt/c/Agentic/god_modules/db/hermes_state.json"

def init_memory():
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'w') as f:
            json.dump({"tasks": {}, "project_context": {}}, f)

def log_task(task_name, status, details=""):
    init_memory()
    with open(MEMORY_FILE, 'r+') as f:
        data = json.load(f)
        data["tasks"][task_name] = {
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()
    print(f"[*] Task '{task_name}' updated to: {status}")

def get_status():
    init_memory()
    with open(MEMORY_FILE, 'r') as f:
        print(json.dumps(json.load(f), indent=4))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python memory_manager.py [log|status] [task_name] [status] [details]")
        sys.exit(1)
    
    action = sys.argv[1]
    if action == "log" and len(sys.argv) >= 4:
        log_task(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
    elif action == "status":
        get_status()

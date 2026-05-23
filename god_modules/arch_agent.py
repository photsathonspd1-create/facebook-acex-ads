import os, sys, json
target = sys.argv[1]
report = {"large_files": [], "todo_count": 0}
for root, _, files in os.walk(target):
    for f in files:
        if f.endswith('.md') or f.endswith('.js') or f.endswith('.py') or f.endswith('.ts'):
            path = os.path.join(root, f)
            size = os.path.getsize(path)
            if size > 50000:
                report["large_files"].append({"file": path, "size": size})
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    report["todo_count"] += content.upper().count('TODO')
            except:
                pass
with open("/mnt/c/Agentic/god_modules/reports/ezdoc_arch.json", 'w') as out:
    json.dump(report, out)

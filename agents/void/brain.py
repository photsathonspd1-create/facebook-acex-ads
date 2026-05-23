import time
import os

print("🔱 VOID AGENT ONLINE")
print("🔱 NODE: Nucha")
print("🔱 MISSION: WAITING FOR MASTER'S DIRECTIVE")

while True:
    if os.path.exists("/tmp/void_mission.txt"):
        with open("/tmp/void_mission.txt", "r") as f:
            mission = f.read()
        print(f"🔥 EXECUTING MISSION: {mission}")
        os.remove("/tmp/void_mission.txt")
    time.sleep(5)

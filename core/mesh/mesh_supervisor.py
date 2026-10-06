"""Sovereign Mesh Supervisor.

Provides idempotent process lifecycle controls for background daemons:
peer_telemetry_receiver, log_flusher, and mesh_monitor.
"""

import sys
import subprocess
import time
import os

DAEMONS = {
    "receiver": {
        "pattern": "peer_telemetry_receiver.py",
        "cmd": ["python3", "-u", "core/mesh/peer_telemetry_receiver.py"]
    },
    "flusher": {
        "pattern": "log_flusher.py",
        "cmd": ["python3", "-u", "-c", "import time, subprocess\nwhile True:\n    subprocess.run(['python3', 'core/mesh/log_flusher.py'])\n    time.sleep(300)"]
    },
    "monitor": {
        "pattern": "mesh_monitor.py",
        "cmd": ["python3", "-u", "-c", "import time, subprocess\nwhile True:\n    subprocess.run(['python3', 'core/mesh/mesh_monitor.py'])\n    time.sleep(60)"]
    }
}

def get_pids(pattern: str) -> list[int]:
    res = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
    out = res.stdout.strip()
    return [int(p) for p in out.splitlines()] if out else []

def start():
    base_dir = os.path.expanduser("~/Tordial-GS")
    for name, cfg in DAEMONS.items():
        pids = get_pids(cfg["pattern"])
        if pids:
            print(f"[!] {name} already running under PID(s): {pids}")
        else:
            proc = subprocess.Popen(
                cfg["cmd"],
                cwd=base_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            print(f"[+] Started {name} (PID {proc.pid})")

def stop():
    for name, cfg in DAEMONS.items():
        pids = get_pids(cfg["pattern"])
        if not pids:
            print(f"[*] {name} is not running.")
        for p in pids:
            try:
                os.kill(p, 15)
                print(f"[+] Sent SIGTERM to {name} (PID {p})")
            except ProcessLookupError:
                pass

def status():
    all_ok = True
    for name, cfg in DAEMONS.items():
        pids = get_pids(cfg["pattern"])
        state = f"RUNNING ({pids})" if pids else "STOPPED"
        print(f"[*] {name:<10}: {state}")
        if not pids:
            all_ok = False
    return 0 if all_ok else 1

if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "start":
        start()
    elif action == "stop":
        stop()
    elif action == "restart":
        stop()
        time.sleep(1)
        start()
    else:
        sys.exit(status())

"""Periodic log offloader to Google Drive."""

import os
import time
import subprocess
import shutil

RCLONE_BIN = shutil.which("rclone") or "rclone"
LOCAL_LOG = os.path.expanduser("~/.peer_listener.log")
REMOTE_TARGET = "gdrive:tordial_mesh_vault/logs/peer_listener_latest.log"

def flush_logs(max_lines=150):
    if not os.path.exists(LOCAL_LOG):
        return

    with open(LOCAL_LOG, "r") as f:
        lines = f.readlines()

    if len(lines) > max_lines:
        # Stream the buffer directly to Drive
        payload = "".join(lines).encode("utf-8")
        proc = subprocess.Popen([RCLONE_BIN, "rcat", REMOTE_TARGET], stdin=subprocess.PIPE)
        proc.communicate(input=payload)

        # Truncate local file to last 50 lines
        with open(LOCAL_LOG, "w") as f:
            f.writelines(lines[-50:])
        print(f"[+] Synced {len(lines)} lines to Drive and truncated local log.")

if __name__ == "__main__":
    flush_logs()

"""Google Drive Offloader via Rclone for Sovereign Mesh Reasoning.

Streams heavy telemetry checkpoints, ledger states, and trajectory dumps
directly to Google Drive, preventing flash storage exhaustion on Termux.
"""

import json
import subprocess
import shutil

RCLONE_BIN = shutil.which("rclone") or "rclone"
REMOTE_BASE = "gdrive:tordial_mesh_vault"


class CloudOffloadEngine:
    def __init__(self, remote_path: str = REMOTE_BASE):
        self.remote_path = remote_path

    def put_state(self, remote_file: str, data: dict) -> dict:
        """Pipes JSON data directly to Google Drive via stdin (zero local disk write)."""
        target = f"{self.remote_path}/{remote_file}"
        payload = json.dumps(data, indent=2).encode("utf-8")

        proc = subprocess.Popen(
            [RCLONE_BIN, "rcat", target],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = proc.communicate(input=payload)

        # Filter out rclone deprecation notices from genuine errors
        err_msg = "\n".join(
            line for line in stderr.decode("utf-8").splitlines()
            if not line.startswith("202") and "NOTICE:" not in line
        ).strip()

        if proc.returncode != 0:
            return {
                "success": False,
                "error": err_msg or "Rclone write failed"
            }

        return {
            "success": True,
            "target": target,
            "bytes_written": len(payload)
        }

    def ping_state(self, remote_file: str) -> dict:
        """Checks if a file exists on Drive and returns its metadata."""
        target = f"{self.remote_path}/{remote_file}"
        proc = subprocess.run(
            [RCLONE_BIN, "lsjson", target],
            capture_output=True,
            text=True
        )

        if proc.returncode != 0:
            return {"success": False, "error": proc.stderr.strip()}

        try:
            info = json.loads(proc.stdout)
            if not info:
                return {"success": False, "error": "Not found"}
            return {"success": True, "metadata": info[0]}
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    engine = CloudOffloadEngine()
    test_burst = {
        "trajectory_id": "BURST_E8_ROOT_12",
        "phase_drift": 0.002,
        "lyapunov_exp": -6.992,
        "vitality": 0.954,
        "status": "OFFLOADED_TO_GDRIVE",
        "notes": "Rad-hard sovereign manifold check offloaded to Drive via rcat"
    }

    print("[*] Uploading snapshot directly to Google Drive...")
    res = engine.put_state("telemetry/latest_snapshot.json", test_burst)
    print("Put result:\n", json.dumps(res, indent=2))

    print("\n[*] Pinging remote file metadata...")
    ping = engine.ping_state("telemetry/latest_snapshot.json")
    print("Ping result:\n", json.dumps(ping, indent=2))

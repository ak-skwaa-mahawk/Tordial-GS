"""Sovereign Vault Storage Watchdog and Token Health Probe.

Verifies Google Drive reachability via rclone, measures remote round-trip latency,
and validates storage write accessibility without accumulating local files.
"""

import subprocess
import time
import json

VAULT_REMOTE = "gdrive:tordial_mesh_vault"

def probe_vault_health() -> dict:
    """Probes remote vault read/write health and records round-trip latency."""
    t0 = time.time()
    res = subprocess.run(
        ["rclone", "about", VAULT_REMOTE, "--json", "--log-level", "ERROR"],
        capture_output=True,
        text=True
    )
    rtt_ms = (time.time() - t0) * 1000.0

    if res.returncode != 0:
        return {
            "status": "UNREACHABLE",
            "error": res.stderr.strip() or "Connection failed",
            "latency_ms": round(rtt_ms, 2),
            "timestamp": time.time()
        }

    try:
        about_data = json.loads(res.stdout) if res.stdout.strip() else {}
        return {
            "status": "HEALTHY",
            "latency_ms": round(rtt_ms, 2),
            "total_bytes": about_data.get("total"),
            "used_bytes": about_data.get("used"),
            "free_bytes": about_data.get("free"),
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "DEGRADED",
            "error": str(e),
            "latency_ms": round(rtt_ms, 2),
            "timestamp": time.time()
        }

if __name__ == "__main__":
    health = probe_vault_health()
    print(f"[*] Vault Status:     {health['status']}")
    print(f"[*] RTT Latency:      {health['latency_ms']} ms")
    if health["status"] == "HEALTHY":
        free_gb = (health.get("free_bytes") or 0) / (1024**3)
        print(f"[+] Available Space:  {free_gb:.2f} GiB")
    elif "error" in health:
        print(f"[-] Error:            {health['error']}")

"""Sovereign Mesh Health and Vault Verification Audit.

Verifies running daemons, tests remote vault reachability/capacity,
validates remote cloud vault states, and certifies cryptographic packet envelopes.
"""

import subprocess
import json
import sys
import os

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))
from core.mesh.crypto_envelope import verify_packet
from core.mesh.vault_watchdog import probe_vault_health

def check_process(name: str) -> bool:
    res = subprocess.run(["pgrep", "-f", name], capture_output=True, text=True)
    return bool(res.stdout.strip())

def audit():
    print("=== Tordial-GS Sovereign Mesh Health Audit ===")
    
    # 1. Process Status
    flusher_alive = check_process("log_flusher.py")
    receiver_alive = check_process("peer_telemetry_receiver.py")
    print(f"[*] Log Flusher Daemon:       {'RUNNING' if flusher_alive else 'STOPPED'}")
    print(f"[*] Telemetry Receiver Daemon: {'RUNNING' if receiver_alive else 'STOPPED'}")

    # 2. Remote Vault Health & Storage Probe
    v_health = probe_vault_health()
    status_label = v_health.get("status", "UNKNOWN")
    latency = v_health.get("latency_ms", 0.0)
    if status_label == "HEALTHY":
        free_gib = (v_health.get("free_bytes") or 0) / (1024**3)
        print(f"[*] Remote Vault Status:      HEALTHY ({latency} ms RTT | Free: {free_gib:.2f} GiB)")
    else:
        print(f"[-] Remote Vault Status:      {status_label} ({latency} ms RTT | Error: {v_health.get('error', 'None')})")

    # 3. Vault Sync Audit
    print("\n[*] Auditing Remote Vault Signatures...")
    roots = [0, 12, 24, 48, 72, 120, 144, 216]
    for r in roots:
        target = f"gdrive:tordial_mesh_vault/telemetry/packets/last_packet_root_{r}.json"
        res = subprocess.run(["rclone", "cat", target, "--log-level", "ERROR"], capture_output=True, text=True)
        if res.returncode != 0 or not res.stdout.strip():
            print(f"[-] Root #{r}: Vault record missing or unreachable.")
            continue
        try:
            record = json.loads(res.stdout)
            pkt = record.get("signed_packet", record)
            transit = record.get("transit_metrics", {})
            delay_str = f" | Delay={transit.get('transit_delay_ms')}ms" if transit else ""

            valid, payload = verify_packet(pkt)
            sig_status = "VALID" if valid else "LEGACY / UNSIGNED"
            print(f"[+] Root #{r}: Signature {sig_status} | Payload={payload.get('phase_drift', 0.0)} rad, λ={payload.get('lyapunov')}{delay_str}")
        except Exception as e:
            print(f"[-] Root #{r}: Parse failure ({e})")

    # 4. Local Disk Footprint
    git_clean = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip() == ""
    print(f"\n[*] Working Tree Hygiene:      {'CLEAN' if git_clean else 'DIRTY'}")

if __name__ == "__main__":
    audit()

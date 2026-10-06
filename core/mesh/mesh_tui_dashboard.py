"""Sovereign Real-Time Terminal Telemetry Dashboard.

Renders an interactive curses-free ANSI terminal interface showing live daemon states,
manifold jitter statistics, individual carrier root invariants, and vault alerts.
"""

import time
import os
import sys
import json
import subprocess

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))
from core.mesh.vault_watchdog import probe_vault_health
from core.mesh.crypto_envelope import verify_packet
from core.mesh.jitter_analyzer import compute_jitter_stats

CARRIER_ROOTS = [0, 12, 24, 48, 72, 120, 144, 216]

def check_daemon(name: str) -> bool:
    res = subprocess.run(["pgrep", "-f", name], capture_output=True, text=True)
    return bool(res.stdout.strip())

def render_dashboard():
    os.system("clear" if os.name != "nt" else "cls")
    now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    print("=" * 70)
    print(f"  TORDIAL-GS SOVEREIGN MESH TELEMETRY DASHBOARD  [{now_str}]")
    print("=" * 70)

    # 1. Daemon Status Block
    flusher = check_daemon("log_flusher.py")
    receiver = check_daemon("peer_telemetry_receiver.py")
    monitor = check_daemon("mesh_monitor.py")
    
    print("\n[PROCESS SUPERVISOR]")
    print(f"  • Ingress Receiver   : {'\033[92mONLINE\033[0m' if receiver else '\033[91mOFFLINE\033[0m'}")
    print(f"  • Vault Log Flusher  : {'\033[92mONLINE\033[0m' if flusher else '\033[91mOFFLINE\033[0m'}")
    print(f"  • Mesh Health Monitor: {'\033[92mONLINE\033[0m' if monitor else '\033[91mOFFLINE\033[0m'}")

    # 2. Vault Storage
    v_stat = probe_vault_health()
    status = v_stat.get("status", "UNKNOWN")
    latency = v_stat.get("latency_ms", 0.0)
    free_gib = (v_stat.get("free_bytes") or 0) / (1024**3)
    status_color = "\033[92m" if status == "HEALTHY" else "\033[91m"
    print(f"\n[REMOTE VAULT STATUS]")
    print(f"  • Health  : {status_color}{status}\033[0m ({latency:.2f} ms RTT)")
    print(f"  • Capacity: {free_gib:.2f} GiB available")

    # 3. Manifold Carrier Root Telemetry
    print(f"\n[CARRIER ROOT MANIFOLD]")
    print(f"  {'ROOT':<6} | {'AUTH':<8} | {'PHASE (rad)':<12} | {'LYAPUNOV (λ)':<13} | {'DELAY (ms)':<10}")
    print("  " + "-" * 60)

    delays = []
    for r in CARRIER_ROOTS:
        target = f"gdrive:tordial_mesh_vault/telemetry/packets/last_packet_root_{r}.json"
        res = subprocess.run(["rclone", "cat", target, "--log-level", "ERROR"], capture_output=True, text=True)
        if res.returncode != 0 or not res.stdout.strip():
            print(f"  #{r:<5} | \033[91mN/A\033[0m     | {'--':<12} | {'--':<13} | {'--':<10}")
            continue

        try:
            record = json.loads(res.stdout)
            pkt = record.get("signed_packet", record)
            transit = record.get("transit_metrics", {})
            valid, payload = verify_packet(pkt)
            delay = transit.get("transit_delay_ms", 0.0)
            delays.append(float(delay))

            auth_str = "\033[92mVALID\033[0m" if valid else "\033[91mINVALID\033[0m"
            drift = payload.get("phase_drift", 0.0)
            lyap = payload.get("lyapunov", -6.992)
            print(f"  #{r:<5} | {auth_str:<17} | {drift:<12.5f} | {lyap:<13.3f} | {delay:<10.3f}")
        except Exception:
            print(f"  #{r:<5} | \033[91mERR\033[0m     | {'--':<12} | {'--':<13} | {'--':<10}")

    if delays:
        stats = compute_jitter_stats(delays)
        print("  " + "-" * 60)
        print(f"  Dispersion: Mean={stats['mean_delay_ms']:.3f}ms | Jitter(σ)={stats['jitter_ms']:.3f}ms | Range=[{stats['min_delay_ms']:.3f}, {stats['max_delay_ms']:.3f}]ms")

    # 4. Recent Alerts Summary
    print(f"\n[VAULT ALERTS]")
    alerts_res = subprocess.run(["rclone", "ls", "gdrive:tordial_mesh_vault/telemetry/alerts", "--log-level", "ERROR"], capture_output=True, text=True)
    alert_lines = alerts_res.stdout.strip().splitlines() if alerts_res.stdout.strip() else []
    print(f"  • Total Logged Events: {len(alert_lines)}")
    if alert_lines:
        latest = alert_lines[-1].split()[-1]
        print(f"  • Latest Incident    : {latest}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    render_dashboard()

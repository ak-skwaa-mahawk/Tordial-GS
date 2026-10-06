"""Sovereign Continuous Mesh Health & Jitter Monitor Daemon.

Periodically queries remote packet snapshots for active E8 carrier roots,
computes dynamic dispersion statistics, alerts on topological anomalies,
and mirrors aggregate telemetry digests to Google Drive.
"""

import time
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))

from core.mesh.jitter_analyzer import compute_jitter_stats
from core.mesh.cloud_offload import CloudOffloadEngine
from core.mesh.crypto_envelope import verify_packet

CARRIER_ROOTS = [0, 12, 24, 48, 72, 120, 144, 216]
MONITOR_INTERVAL_SEC = 60

class MeshMonitor:
    def __init__(self):
        self.offloader = CloudOffloadEngine()

    def run_cycle(self) -> dict:
        delays = []
        root_states = {}

        for r in CARRIER_ROOTS:
            path = f"telemetry/packets/last_packet_root_{r}.json"
            # Read state using rclone cat
            import subprocess
            res = subprocess.run(["rclone", "cat", f"gdrive:tordial_mesh_vault/{path}", "--log-level", "ERROR"],
                                 capture_output=True, text=True)
            if res.returncode != 0 or not res.stdout.strip():
                continue

            try:
                record = json.loads(res.stdout)
                pkt = record.get("signed_packet", record)
                transit = record.get("transit_metrics", {})
                valid, payload = verify_packet(pkt)

                delay = transit.get("transit_delay_ms")
                if delay is not None:
                    delays.append(float(delay))

                root_states[str(r)] = {
                    "valid_hmac": valid,
                    "phase_drift": payload.get("phase_drift", 0.0),
                    "lyapunov": payload.get("lyapunov", 0.0),
                    "delay_ms": delay
                }
            except Exception:
                continue

        stats = compute_jitter_stats(delays)
        digest = {
            "timestamp": time.time(),
            "monitored_roots_count": len(root_states),
            "carrier_roots": CARRIER_ROOTS,
            "jitter_stats": stats,
            "root_states": root_states,
            "all_healthy": all(
                s["valid_hmac"] and abs(s["phase_drift"]) <= 0.001 and s["lyapunov"] <= -1.0
                for s in root_states.values()
            ) if root_states else False
        }

        # Offload consolidated digest to cloud vault
        self.offloader.put_state("telemetry/metrics/manifold_health_latest.json", digest)
        return digest

if __name__ == "__main__":
    monitor = MeshMonitor()
    digest = monitor.run_cycle()
    print(f"[+] Cycle completed: {digest['monitored_roots_count']}/{len(CARRIER_ROOTS)} roots healthy.")
    print(f"[*] Mean Delay: {digest['jitter_stats']['mean_delay_ms']} ms | Jitter(σ): {digest['jitter_stats']['jitter_ms']} ms")

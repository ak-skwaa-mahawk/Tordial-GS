"""Autonomous Mesh Telemetry Ingest & Router Loop with Failure Retry.

Monitors active peer states, evaluates anomalous metric drift using
E8GeodesicRouter, and offloads verified decision journals to Google Drive.
"""

import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))

from core.mesh.e8_router import E8GeodesicRouter

def run_telemetry_cycle(max_cycle_retries: int = 2):
    router = E8GeodesicRouter()
    print("[+] Mesh Evaluator listening to sovereign carrier field...")

    active_indices = [12, 48, 120]
    pending = list(active_indices)

    for cycle in range(1, max_cycle_retries + 1):
        if not pending:
            break

        failed = []
        for idx in pending:
            print(f"[*] [Cycle {cycle}] Verifying stability for Root Vector #{idx}...")
            res = router.evaluate_vector(
                root_index=idx,
                phase_drift=0.00000,
                lyapunov=-6.992
            )

            if res.get("success"):
                print(f"[+] Root #{idx} Evaluation complete: STABLE -> {res.get('cloud_offload', {}).get('target')}")
            else:
                print(f"[-] Root #{idx} Evaluation transient fail, queueing retry...")
                failed.append(idx)

        pending = failed
        if pending and cycle < max_cycle_retries:
            time.sleep(3.0)

    print("[*] Telemetry cycle finalized.")

if __name__ == "__main__":
    run_telemetry_cycle()

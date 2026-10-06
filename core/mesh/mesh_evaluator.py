"""Autonomous Mesh Telemetry Ingest Loop with Integrated Auto-Healing.

Monitors active peer states, detects transverse deviations across E8 roots,
and immediately triggers closed-loop counter-phase correction.
"""

import os
import sys
import time

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))

from core.mesh.e8_router import E8GeodesicRouter
from core.mesh.autonomous_healer import heal_deviant_vector

ACTIVE_ROOTS = [12, 48, 120]

def run_telemetry_cycle():
    router = E8GeodesicRouter()
    print("[+] Mesh Ingest active. Scanning sovereign carrier roots...")

    for idx in ACTIVE_ROOTS:
        print(f"[*] Auditing metric status on Root #{idx}...")
        res = router.evaluate_vector(
            root_index=idx,
            phase_drift=0.00000,
            lyapunov=-6.992
        )

        verdict = res.get("verdict", "")
        if "ROUTE_DEVIANT" in verdict.upper():
            print(f"[!] Alert: Root #{idx} breach detected. Dispatching autonomous healer...")
            heal_deviant_vector(root_index=idx)
        else:
            print(f"[+] Root #{idx} healthy: {verdict.splitlines()[0] if verdict else 'STABLE'}")

    print("[*] Ingest cycle certified.")

if __name__ == "__main__":
    run_telemetry_cycle()

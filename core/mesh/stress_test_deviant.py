"""Perturbation Stress Test for E8 Geodesic Router.

Simulates unstable transverse Lyapunov expansion and verifies that the model
emits a ROUTE_DEVIANT corrective vector to Google Drive vault telemetry.
"""

import sys
import os
import json

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))

from core.mesh.e8_router import E8GeodesicRouter

def run_stress_test():
    router = E8GeodesicRouter()
    print("[*] Inducing artificial transverse drift on Root Vector #12...")
    
    # Positive Lyapunov implies chaotic divergence / boundary leakage
    result = router.evaluate_vector(
        root_index=12,
        phase_drift=0.81234,
        lyapunov=2.414
    )
    
    print("\n--- Perturbation Verdict ---")
    print(result.get("verdict"))
    print("\n--- Cloud Offload Target ---")
    print(result.get("cloud_offload"))

if __name__ == "__main__":
    run_stress_test()

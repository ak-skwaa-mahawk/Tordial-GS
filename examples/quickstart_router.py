#!/usr/bin/env python3
"""
Minimal standalone example demonstrating 8D state-space edge routing.
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from core.mesh.router import SovereignMeshRouter

def main():
    print("[*] Initializing SovereignMeshRouter node...")
    router = SovereignMeshRouter(node_id="LOCAL-NODE-01")

    # 8D telemetry vector:
    # [latency, queue, thermal, battery, packet_loss, bandwidth, memory, compute_load]
    telemetry_state = np.array([4.0, 3.0, 0.01, 0.02, 3.5, 0.98, 0.2, 0.002], dtype=float)

    print(f"[*] Input Telemetry State: {telemetry_state}")

    # Execute single route dispatch
    result = router.route_burst(telemetry_state, budget_sats=500)
    decision = result.get("decision", {})

    print("\n--- Routing Result ---")
    print(f"Node ID          : {result.get('node_id')}")
    print(f"Budget           : {result.get('budget_sats')} sats")
    print(f"Status           : {decision.get('status')}")
    print(f"Selected Root    : #{decision.get('selected_root_index')}")
    print(f"Dispatch Weight  : {decision.get('dispatch_weight'):.4f}")
    print(f"State Mass Norm  : {decision.get('mass_norm'):.4f}")
    print(f"Phase Drift      : {decision.get('phase_drift')}")

if __name__ == "__main__":
    main()

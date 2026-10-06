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

    # Synthetic 8D telemetry vector:
    # [latency, queue, thermal, battery, packet_loss, bandwidth, memory, compute_load]
    telemetry_state = np.array([4.0, 3.0, 0.01, 0.02, 3.5, 0.98, 0.2, 0.002], dtype=float)

    print(f"[*] Input Telemetry State: {telemetry_state}")
    
    # Execute single route dispatch
    result = router.route_burst(telemetry_state, budget_sats=500)

    print("\n--- Routing Result ---")
    print(f"Status           : {result.get('status')}")
    print(f"Allocated Route  : {result.get('route')}")
    print(f"Fee Allocation   : {result.get('allocations')}")
    print(f"Residual Balance : {result.get('settled_balance', 'OK')}")

if __name__ == "__main__":
    main()

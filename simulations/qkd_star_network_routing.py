import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_star_network_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-STAR-NETWORK-ROUTING"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_star_routing_matrix",
            "hypothesis": "Model 4-user star quantum network switch dynamically scheduling BSM routing matrix",
            "parameters": {
                "nodes": ["Yale", "StonyBrook", "NewLondon", "BNL"],
                "hub": "FalknerIsland",
                "rounds": 30000
            }
        }
    )

    sim_code = """
import json
import numpy as np

np.random.seed(42)
N_rounds = 30000

# Network Topology & Optical Link Distances to Central Hub (Falkner Island)
clients = ["Yale", "StonyBrook", "NewLondon", "BNL"]
distances_km = {
    "Yale": 19.8,
    "StonyBrook": 28.5,
    "NewLondon": 38.2,
    "BNL": 34.0
}

alpha_db = 0.45
eta_det = 0.85
M_modes = 50

# Calculate channel transmittances for each radial branch
eta_branches = {}
for node, d in distances_km.items():
    loss_db = alpha_db * d
    eta_branches[node] = (10 ** (-loss_db / 10.0)) * eta_det

# Traffic Demand Matrix (Requested connections per round)
# Target pairs: (Yale <-> StonyBrook), (Yale <-> BNL), (NewLondon <-> StonyBrook)
traffic_requests = [
    ("Yale", "StonyBrook"),
    ("Yale", "BNL"),
    ("NewLondon", "StonyBrook")
]

p_bsm = 0.50
bsm_visibility = 0.98
memory_fidelity_0 = 0.995

# Telemetry Accumulators
routed_pairs = {f"{u1}-{u2}": 0 for u1, u2 in traffic_requests}
errors_pairs = {f"{u1}-{u2}": 0 for u1, u2 in traffic_requests}

for _ in range(N_rounds):
    # Step 1: Heralding attempts on all branches
    active_heralds = {}
    for node, eta in eta_branches.items():
        heralds = np.where(np.random.rand(M_modes) < eta)[0]
        active_heralds[node] = heralds[0] if len(heralds) > 0 else None

    # Step 2: Dynamic Switch Routing (Greedy matching by demand order)
    matched_nodes = set()
    for u1, u2 in traffic_requests:
        pair_key = f"{u1}-{u2}"
        if u1 not in matched_nodes and u2 not in matched_nodes:
            if active_heralds[u1] is not None and active_heralds[u2] is not None:
                matched_nodes.add(u1)
                matched_nodes.add(u2)
                
                # Execute BSM at Hub
                if np.random.rand() < p_bsm:
                    routed_pairs[pair_key] += 1
                    
                    wait_diff = abs(active_heralds[u1] - active_heralds[u2])
                    dephasing = np.exp(-2.0 * (wait_diff / 500.0))
                    eff_fidelity = memory_fidelity_0 * dephasing
                    
                    depol = (4.0 * eff_fidelity - 1.0) / 3.0
                    W = (depol ** 2) * bsm_visibility
                    err_p = max(0.0, (1.0 - W) / 2.0)
                    if np.random.rand() < err_p:
                        errors_pairs[pair_key] += 1

def H2(p):
    return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)

f_EC = 1.15
metrics_by_pair = {}

for pair_key in routed_pairs:
    count = routed_pairs[pair_key]
    errs = errors_pairs[pair_key]
    swap_rate = count / N_rounds
    qber = errs / max(count, 1)
    key_frac = max(0.0, 1.0 - (1.0 + f_EC) * H2(qber))
    skr = swap_rate * key_frac
    
    metrics_by_pair[pair_key] = {
        "established_swaps": count,
        "swap_rate_per_round": round(float(swap_rate), 5),
        "qber": round(float(qber), 4),
        "secret_key_rate": round(float(skr), 6)
    }

telemetry = {
    "hub_node": "FalknerIsland",
    "active_clients": clients,
    "branch_transmittances": {k: round(float(v), 5) for k, v in eta_branches.items()},
    "traffic_performance": metrics_by_pair
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "star_network_routing_eval", "code": sim_code}
    )

    print("\n=== Multi-User Star Quantum Network Routing Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_star_network_simulation())

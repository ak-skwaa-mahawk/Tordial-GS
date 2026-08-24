import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_asymmetric_chain_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-ASYMMETRIC-3NODE-CHAIN"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_asymmetric_repeater_mesh",
            "hypothesis": "Model 4-segment asymmetric quantum repeater chain across Long Island Sound with memory buffer decoherence",
            "parameters": {
                "segment_lengths_km": [16.0, 12.5, 13.0, 6.78],
                "modes_M": 50,
                "memory_T2_ms": 10.0
            }
        }
    )

    sim_code = """
import json
import numpy as np

np.random.seed(42)
N_rounds = 50000

# Geographical Segments across Long Island Sound (km)
# Shoreham (Alice) -> Node 1 -> Node 2 (Falkner Is.) -> Node 3 (Thimble Is.) -> Yale (Bob)
segment_lengths = [16.0, 12.5, 13.0, 6.78]
total_distance = sum(segment_lengths)

alpha_db = 0.45  # dB/km atmospheric/marine extinction
eta_det = 0.85
M_modes = 50     # Temporal multiplexing modes

# Segment transmittances
segment_losses_db = [alpha_db * d for d in segment_lengths]
eta_segments = [(10 ** (-loss / 10.0)) * eta_det for loss in segment_losses_db]

# End-to-end direct benchmark
eta_direct = (10 ** (-(alpha_db * total_distance) / 10.0)) * (eta_det ** 2)
plob_bound = -np.log2(1.0 - eta_direct)

# Repeater Node Hardware Specifications
p_bsm = 0.50             # Linear Bell State Measurement efficiency
bsm_visibility = 0.98    # Hong-Ou-Mandel visibility
memory_fidelity_0 = 0.995
coherence_time_bins = 1000

successful_end_to_end_swaps = 0
total_errors = 0

for _ in range(N_rounds):
    # Step 1: Attempt entanglement generation on all 4 segments across M modes
    arrival_times = []
    seg_success = True
    
    for eta_seg in eta_segments:
        heralds = np.where(np.random.rand(M_modes) < eta_seg)[0]
        if len(heralds) > 0:
            arrival_times.append(heralds[0])
        else:
            seg_success = False
            break
            
    if not seg_success:
        continue
        
    # Step 2: Perform 3 sequential/nested Bell State Measurements across Nodes 1, 2, and 3
    # Probability of all 3 BSMs succeeding: (p_bsm)^3 = 0.125
    if np.random.rand() < (p_bsm ** 3):
        successful_end_to_end_swaps += 1
        
        # Calculate asymmetric memory wait time (delay between fastest and slowest links)
        max_wait = max(arrival_times) - min(arrival_times)
        
        # Cumulative memory decoherence across all 3 nodes
        mem_decay = np.exp(-3.0 * (max_wait / coherence_time_bins))
        effective_fidelity = memory_fidelity_0 * mem_decay
        
        # Swapped Werner parameter across 3 cascaded BSM operations
        depol = (4.0 * effective_fidelity - 1.0) / 3.0
        W_total = (depol ** 4) * (bsm_visibility ** 3)
        
        # End-to-end QBER on the established Alice-Bob pair
        error_prob = max(0.0, (1.0 - W_total) / 2.0)
        if np.random.rand() < error_prob:
            total_errors += 1

swap_rate = successful_end_to_end_swaps / N_rounds
qber = total_errors / max(successful_end_to_end_swaps, 1)

def H2(p):
    return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)

f_EC = 1.15
key_fraction = max(0.0, 1.0 - (1.0 + f_EC) * H2(qber))
secret_key_rate = swap_rate * key_fraction

results = {
    "chain_topology": "4-Segment 3-Repeater Chain (Shoreham -> Falkner -> Thimbles -> Yale)",
    "segment_lengths_km": segment_lengths,
    "segment_transmittances": [round(float(e), 5) for e in eta_segments],
    "multiplexed_modes_M": M_modes,
    "plob_direct_bound": round(float(plob_bound), 6),
    "end_to_end_swap_rate": round(float(swap_rate), 6),
    "end_to_end_qber": round(float(qber), 4),
    "secret_key_rate": round(float(secret_key_rate), 6),
    "repeater_advantage_over_plob": round(float(secret_key_rate / plob_bound), 2)
}

print(f"__METRICS__={json.dumps(results)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "asymmetric_3node_chain_eval", "code": sim_code}
    )

    print("\n=== Asymmetric 3-Node Repeater Chain Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_asymmetric_chain_simulation())

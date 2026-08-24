import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_multiplexed_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-MULTIPLEXED-REPEATER-PLOB"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_temporal_multiplexing_sweep",
            "hypothesis": "Model M temporal memory modes to scale entanglement swap yield beyond the fundamental PLOB limit",
            "parameters": {"total_distance_km": 48.28, "modes_sweep": [1, 10, 50, 100, 250]}
        }
    )

    sim_code = """
import json
import numpy as np

np.random.seed(42)
N_rounds = 50000

# Channel Parameters: 48.28 km split into two 24.14 km segments
L_total = 48.28
L_seg = L_total / 2.0
alpha_db = 0.45  # dB/km atmospheric/marine extinction

loss_db_seg = alpha_db * L_seg
loss_db_total = alpha_db * L_total

eta_det = 0.85
eta_seg = (10 ** (-loss_db_seg / 10.0)) * eta_det       # ~0.0697 per segment
eta_total = (10 ** (-loss_db_total / 10.0)) * (eta_det**2) # ~0.00486 direct link

# Fundamental Direct Capacity Benchmark (PLOB bound)
plob_bound = -np.log2(1.0 - eta_total)

# Quantum Memory & BSM Parameters
p_bsm = 0.50             # Linear optics BSM
bsm_visibility = 0.97    # Hong-Ou-Mandel visibility
memory_fidelity_0 = 0.99 # Base memory fidelity
coherence_time_bins = 500 # Memory dephasing scale in time-bins

def evaluate_multiplexing(M_modes):
    successful_swaps = 0
    errors = 0

    for _ in range(N_rounds):
        # Generate heralded attempts across M temporal modes per segment
        seg1_attempts = np.random.rand(M_modes) < eta_seg
        seg2_attempts = np.random.rand(M_modes) < eta_seg

        # Check if both segments successfully heralded at least one mode
        if np.any(seg1_attempts) and np.any(seg2_attempts):
            idx1 = np.where(seg1_attempts)[0][0]
            idx2 = np.where(seg2_attempts)[0][0]
            
            # Storage time difference between arrivals causes dephasing
            delta_storage_bins = abs(idx1 - idx2)
            mem_fidelity = memory_fidelity_0 * np.exp(-delta_storage_bins / coherence_time_bins)
            
            # Linear BSM swap attempt
            if np.random.rand() < p_bsm:
                successful_swaps += 1
                depol = (4.0 * mem_fidelity - 1.0) / 3.0
                W = depol * bsm_visibility
                error_prob = max(0.0, (1.0 - W) / 2.0)
                if np.random.rand() < error_prob:
                    errors += 1

    rate_per_round = successful_swaps / N_rounds
    qber = errors / max(successful_swaps, 1)

    def H2(p):
        return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)

    f_EC = 1.15
    key_fraction = max(0.0, 1.0 - (1.0 + f_EC) * H2(qber))
    skr = rate_per_round * key_fraction

    return {
        "modes_M": M_modes,
        "swap_rate_per_round": round(float(rate_per_round), 6),
        "qber": round(float(qber), 4),
        "secret_key_rate": round(float(skr), 6),
        "plob_ratio": round(float(skr / plob_bound), 3),
        "beats_plob": bool(skr > plob_bound)
    }

results = {
    "plob_capacity_bound": round(float(plob_bound), 6),
    "mode_evaluations": [evaluate_multiplexing(m) for m in [1, 10, 50, 100, 250]]
}

print(f"__METRICS__={json.dumps(results)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "multiplexed_repeater_sweep", "code": sim_code}
    )

    print("\n=== Temporal Multiplexed Repeater & PLOB Benchmark Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_multiplexed_simulation())

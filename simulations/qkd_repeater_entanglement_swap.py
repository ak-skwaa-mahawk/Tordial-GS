import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_repeater_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-REPEATER-ENTANGLEMENT-SWAP"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_midpoint_bsm_swap",
            "hypothesis": "Model entanglement swapping repeater at mid-span of 30-mile Long Island Sound link",
            "parameters": {"total_distance_km": 48.28, "segments": 2, "quantum_memory_fidelity": 0.98}
        }
    )

    repeater_sim_code = """
import json
import numpy as np

np.random.seed(42)
N_trials = 100000

# Channel Parameters: 48.28 km split into two 24.14 km half-links (Alice->Repeater, Repeater->Bob)
L_total = 48280.0
L_seg = L_total / 2.0   # 24,140 meters per segment

# Extinction per segment (0.45 dB/km)
loss_db_seg = 0.45 * (L_seg / 1000.0) # ~10.86 dB per leg
eta_channel_seg = 10 ** (-loss_db_seg / 10.0) # ~0.082 transmittance

# Segment AO tracking and detector efficiency
eta_det = 0.85
eta_link = eta_channel_seg * eta_det  # ~0.070 per photon

# Single-Photon Entanglement Generation & Coupling
# Probability of successfully establishing pair A-R1 and pair R2-B
p_pair_A_R1 = eta_link
p_pair_R2_B = eta_link

# Linear Optics Bell State Measurement (BSM) Success Rate at Repeater (max 50% without nonlinear ancilla)
p_bsm = 0.50
bsm_visibility = 0.965  # Two-photon Hong-Ou-Mandel interference visibility

# Quantum Memory Coherence & Depolarizing Channel
memory_fidelity = 0.985
depolarizing_param = (4.0 * memory_fidelity - 1.0) / 3.0

# Simulate Entanglement Swapping Trials
success_swaps = 0
errors = 0

for _ in range(N_trials):
    # Both half-links must successfully deliver photons in the same cycle/coincidence window
    link1_ok = np.random.rand() < p_pair_A_R1
    link2_ok = np.random.rand() < p_pair_R2_B
    
    if link1_ok and link2_ok:
        # Perform BSM at mid-node
        if np.random.rand() < p_bsm:
            success_swaps += 1
            # Effective Werner state parameter after memory storage and BSM imperfect visibility
            W = depolarizing_param * bsm_visibility
            # QBER on swapped entanglement pair: e = (1 - W) / 2
            error_prob = (1.0 - W) / 2.0
            if np.random.rand() < error_prob:
                errors += 1

swap_yield = success_swaps / N_trials
qber = errors / max(success_swaps, 1)

# Asymptotic BBM92 Secret Key Fraction: r = 1 - 2 * H2(qber)
def H2(p):
    return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)

f_EC = 1.15
r_fraction = max(0.0, 1.0 - (1.0 + f_EC) * H2(qber))
secret_key_rate = swap_yield * r_fraction

# Direct Transmission Benchmark (No Repeater over full 48.3 km)
eta_direct = 10 ** (-(0.45 * 48.28) / 10.0) * (eta_det ** 2)
direct_key_rate_upper_bound = -np.log2(1.0 - eta_direct) if eta_direct < 1.0 else 0.0

telemetry = {
    "repeater_topology": "Dual-Segment 1-Node Entanglement Swapping (24.1 km + 24.1 km)",
    "segment_transmittance_eta": round(float(eta_channel_seg), 5),
    "entanglement_swap_yield": round(float(swap_yield), 6),
    "swapped_pair_qber": round(float(qber), 4),
    "secret_key_rate_per_cycle": round(float(secret_key_rate), 7),
    "direct_unrepeatered_key_rate": round(float(direct_key_rate_upper_bound), 7),
    "repeater_advantage_ratio": round(float(secret_key_rate / max(direct_key_rate_upper_bound, 1e-9)), 2),
    "link_status": "REPEATER_OPERATIONAL"
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "repeater_swap_eval", "code": repeater_sim_code}
    )

    print("\n=== Quantum Repeater Entanglement Swapping Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_repeater_simulation())

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_nuclear_register_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-NV-NUCLEAR-AUX-REGISTER"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_nuclear_storage_dynamics",
            "hypothesis": "Model 14N nuclear spin auxiliary register extending memory coherence past 10 seconds for asynchronous repeater networks",
            "parameters": {
                "nuclear_T2_s": 12.0,
                "swap_gate_fidelity": 0.985,
                "swap_gate_duration_us": 25.0
            }
        }
    )

    sim_code = """
import json
import numpy as np

np.random.seed(42)
N_trials = 50000

# NV Center & 14N Nuclear Memory Parameters
T2_electron_ms = 100.0        # Electron spin coherence with XY8 (0.1 s)
T2_nuclear_s = 12.0           # 14N Nuclear spin coherence with RF decoupling (12.0 s)
F_swap_gate = 0.985           # SWAP gate fidelity (e- -> 14N)
gate_duration_ms = 0.025      # 25 us per SWAP

# Optical Link Parameters across Long Island Sound (24.1 km per segment)
eta_herald_prob = 0.0087      # Single attempt heralded detection prob at 1550nm
p_bsm = 0.50
bsm_visibility = 0.98

# Repetition rate: 100 kHz attempt cycle (10 us per cycle)
attempt_cycle_ms = 0.010

def evaluate_memory_architecture(use_nuclear_register=True, max_waiting_attempts=5000):
    successful_swaps = 0
    total_errors = 0

    for _ in range(N_trials):
        # Asynchronous link establishment: Segment 1 and Segment 2
        # Geometric distribution for attempts until success:
        attempts_A = np.random.geometric(eta_herald_prob)
        attempts_B = np.random.geometric(eta_herald_prob)
        
        # If either segment exceeds maximum buffer capacity, drop and reset
        if attempts_A > max_waiting_attempts or attempts_B > max_waiting_attempts:
            continue
            
        delta_attempts = abs(attempts_A - attempts_B)
        wait_time_ms = delta_attempts * attempt_cycle_ms
        
        if use_nuclear_register:
            # Transfer e- state to 14N, wait, and transfer back to e-
            # State experiences 2 SWAP gates (Write + Read)
            gate_fidelity_penalty = F_swap_gate ** 2
            
            # 14N nuclear dephasing (Gaussian dephasing profile)
            wait_time_s = wait_time_ms / 1000.0
            nuclear_dephasing = np.exp(-(wait_time_s / T2_nuclear_s) ** 2)
            
            effective_mem_fidelity = 0.995 * gate_fidelity_penalty * nuclear_dephasing
        else:
            # Electron spin storage only (no auxiliary register)
            electron_dephasing = np.exp(-(wait_time_ms / T2_electron_ms) ** 2)
            effective_mem_fidelity = 0.995 * electron_dephasing

        # Check if quantum state survived above classical threshold (F > 0.5)
        if effective_mem_fidelity < 0.5:
            continue

        # Perform Bell State Measurement at repeater
        if np.random.rand() < p_bsm:
            successful_swaps += 1
            
            # Resulting Werner state parameter
            depol = max(0.0, (4.0 * effective_mem_fidelity - 1.0) / 3.0)
            W_pair = (depol ** 2) * bsm_visibility
            
            error_prob = max(0.0, (1.0 - W_pair) / 2.0)
            if np.random.rand() < error_prob:
                total_errors += 1

    swap_yield = successful_swaps / N_trials
    qber = total_errors / max(successful_swaps, 1)

    def H2(p):
        return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)

    f_EC = 1.15
    key_fraction = max(0.0, 1.0 - (1.0 + f_EC) * H2(qber))
    secret_key_rate = swap_yield * key_fraction

    return {
        "swap_yield": round(float(swap_yield), 6),
        "qber": round(float(qber), 4),
        "secret_key_rate": round(float(secret_key_rate), 6),
        "link_operational": bool(secret_key_rate > 1e-6)
    }

results = {
    "electron_only_storage": evaluate_memory_architecture(use_nuclear_register=False),
    "14N_nuclear_auxiliary_register": evaluate_memory_architecture(use_nuclear_register=True)
}

print(f"__METRICS__={json.dumps(results)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "nv_nuclear_reg_eval", "code": sim_code}
    )

    print("\n=== Diamond NV 14N Nuclear Auxiliary Register Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_nuclear_register_simulation())

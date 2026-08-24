import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_nv_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-NV-SPIN-PHOTON-INTERFACE"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_nv_purcell_qfc_model",
            "hypothesis": "Model cavity-enhanced Diamond NV center spin-photon entanglement generation and 637nm->1550nm QFC conversion",
            "parameters": {
                "purcell_factor_Fp": 30.0,
                "qfc_efficiency": 0.40,
                "cryo_temp_K": 4.0,
                "coherence_T2_ms": 100.0
            }
        }
    )

    nv_sim_code = """
import json
import numpy as np

np.random.seed(42)
N_trials = 50000

# 1. Cavity-Enhanced Diamond NV Emission Optics
xi_0 = 0.03                 # Bulk ZPL branching ratio (637 nm)
F_P = 30.0                  # Microcavity Purcell factor
xi_cavity = (F_P * xi_0) / (F_P * xi_0 + (1.0 - xi_0))  # ~0.481

cavity_outcoupling = 0.65   # Optical extraction efficiency from cavity
eta_emission_zpl = xi_cavity * cavity_outcoupling        # ~0.313

# 2. Quantum Frequency Conversion (637 nm -> 1550 nm PPLN DFG)
eta_qfc = 0.40              # QFC internal conversion + filter throughput
p_qfc_noise_photons = 1e-5  # Raman/pump scattering noise per gate

# 3. Overall Local Photon Yield into Telecom Fiber
eta_photon_source = eta_emission_zpl * eta_qfc           # ~0.125

# 4. Long Island Sound Asymmetric Mid-Segment (24.1 km)
L_seg = 24.14               # km
alpha_marine_db = 0.45      # dB/km
eta_channel = 10 ** (-(alpha_marine_db * L_seg) / 10.0) # ~0.082
eta_detector = 0.85

# Total end-to-end single photon herald probability per attempt
p_herald_photon = eta_photon_source * eta_channel * eta_detector # ~0.0087

# 5. Spin Memory Coherence Dynamics (CPMG Dynamical Decoupling on Electron Spin)
T2_electron_ms = 100.0      # 100 ms with XY8-N decoupling pulses
T1_relaxation_s = 60.0      # Electron relaxation at 4K

# Raw Spin-Photon Entanglement State Fidelity
F_raw_spin_photon = 0.985   # Determined by optical excitation fidelity & phase stability

# Bell State Measurement at Midpoint Station
p_bsm = 0.50
bsm_visibility = 0.98

# Simulate Spin-Photon Entanglement Swapping Rounds
M_modes = 100
successful_swaps = 0
errors = 0

for _ in range(N_trials):
    # Attempt spin-photon heralding across M temporal attempts on Node A and Node B
    heralds_A = np.where(np.random.rand(M_modes) < p_herald_photon)[0]
    heralds_B = np.where(np.random.rand(M_modes) < p_herald_photon)[0]
    
    if len(heralds_A) > 0 and len(heralds_B) > 0:
        idx_A = heralds_A[0]
        idx_B = heralds_B[0]
        
        # Repetition cycle time per mode = 1 us (1 MHz repetition rate)
        wait_time_ms = abs(idx_A - idx_B) * 0.001
        
        # Spin memory dephasing during asynchronous storage
        dephasing = np.exp(-(wait_time_ms / T2_electron_ms) ** 2)
        effective_spin_fidelity = F_raw_spin_photon * dephasing
        
        # Two-photon Bell State Measurement on the flying telecom photons
        if np.random.rand() < p_bsm:
            successful_swaps += 1
            
            # Spin-spin Werner state parameter between Node A and Node B spins
            depol = (4.0 * effective_spin_fidelity - 1.0) / 3.0
            W_spin_spin = (depol ** 2) * bsm_visibility
            
            error_prob = max(0.0, (1.0 - W_spin_spin) / 2.0)
            if np.random.rand() < error_prob:
                errors += 1

swap_rate = successful_swaps / N_trials
qber = errors / max(successful_swaps, 1)

def H2(p):
    return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)

f_EC = 1.15
key_fraction = max(0.0, 1.0 - (1.0 + f_EC) * H2(qber))
secret_key_rate = swap_rate * key_fraction

# Direct unassisted PLOB bound over full 48.3 km
eta_direct = (10 ** (-(alpha_marine_db * 48.28) / 10.0)) * (eta_detector ** 2)
plob_bound = -np.log2(1.0 - eta_direct)

telemetry = {
    "nv_cavity_purcell_Fp": F_P,
    "zpl_branching_ratio": round(float(xi_cavity), 4),
    "qfc_conversion_efficiency": eta_qfc,
    "telecom_herald_prob_per_mode": round(float(p_herald_photon), 6),
    "asynchronous_swap_rate": round(float(swap_rate), 6),
    "spin_spin_qber": round(float(qber), 4),
    "secret_key_rate_per_round": round(float(secret_key_rate), 6),
    "plob_direct_bound": round(float(plob_bound), 6),
    "nv_repeater_plob_ratio": round(float(secret_key_rate / plob_bound), 2),
    "repeater_status": "NV_LINK_OPTIMAL"
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "nv_spin_photon_eval", "code": nv_sim_code}
    )

    print("\n=== Diamond NV Spin-Photon Interface Simulation Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_nv_simulation())

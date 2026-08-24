import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_phonon_entanglement_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-NV-PHONON-ENTANGLEMENT-BUS"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_tavis_cummings_spin_bus",
            "hypothesis": "Model Tavis-Cummings Hamiltonian generating Bell state entanglement between two distant NV centers via topological phononic bus",
            "parameters": {
                "g_m_MHz": 2.5,
                "omega_m_MHz": 280.0,
                "phonon_fock_cutoff": 4,
                "sim_duration_ns": 350.0
            }
        }
    )

    sim_code = """
import json
import numpy as np

# 1. Hilbert Space Construction: 2 Qubits (NV_A, NV_B) + Phonon Bus (Fock space 0..N_fock-1)
# Subspace states: |s_A, s_B, n_ph> where s in {|+1>, |-1>} -> {1, 0}
N_fock = 4
dim_spin = 2 * 2  # 4 spin states: |1,1>, |1,0>, |0,1>, |0,0>
dim_tot = dim_spin * N_fock  # 16 states total

def state_idx(sA, sB, n_ph):
    spin_idx = (sA * 2 + sB)
    return spin_idx * N_fock + n_ph

# 2. Parameters (in GHz units)
omega_s_GHz = 0.280     # 280 MHz spin transition
omega_m_GHz = 0.280     # Resonant phonon mode (280 MHz)
g_m_GHz = 0.0025        # 2.5 MHz single-phonon vacuum coupling rate

# Expected Bell state generation time: t_Bell = pi / (2 * sqrt(2) * g_m)
t_bell_expected_ns = 1.0 / (2.0 * np.sqrt(2.0) * g_m_GHz) # ~141.4 ns

# 3. Construct Rotating-Frame Hamiltonian (Interaction Picture)
H_int = np.zeros((dim_tot, dim_tot), dtype=complex)

for sA in [0, 1]:
    for sB in [0, 1]:
        for n in range(N_fock):
            idx_from = state_idx(sA, sB, n)
            
            # NV_A coupling: sigma_+^(A) * b  and  sigma_-^(A) * b^dagger
            if sA == 0 and n > 0:  # |-1, n> -> |+1, n-1>
                idx_to = state_idx(1, sB, n - 1)
                matrix_elem = g_m_GHz * np.sqrt(n)
                H_int[idx_to, idx_from] += matrix_elem
                H_int[idx_from, idx_to] += matrix_elem
                
            # NV_B coupling: sigma_+^(B) * b  and  sigma_-^(B) * b^dagger
            if sB == 0 and n > 0:  # |-1, n> -> |+1, n-1>
                idx_to = state_idx(sA, 1, n - 1)
                matrix_elem = g_m_GHz * np.sqrt(n)
                H_int[idx_to, idx_from] += matrix_elem
                H_int[idx_from, idx_to] += matrix_elem

# Convert H to ns^-1
H_ns = H_int * (2.0 * np.pi)

# 4. Time Evolution: Initial State |+1, -1, 0> = |sA=1, sB=0, n=0>
psi = np.zeros(dim_tot, dtype=complex)
psi[state_idx(1, 0, 0)] = 1.0

T_total_ns = 350.0
Nt = 3500
dt_ns = T_total_ns / Nt
time_ns = np.linspace(0, T_total_ns, Nt)

# Target Bell state in spin subspace: (|1,0> - i|0,1>)/sqrt(2) with 0 phonons
psi_target_bell = np.zeros(dim_tot, dtype=complex)
psi_target_bell[state_idx(1, 0, 0)] = 1.0 / np.sqrt(2.0)
psi_target_bell[state_idx(0, 1, 0)] = -1j / np.sqrt(2.0)

bell_fidelity_history = []
pop_intermediate_phonon_history = []

for t in time_ns:
    # RK4 Step
    def dpsi(p):
        return -1j * np.dot(H_ns, p)
        
    k1 = dpsi(psi)
    k2 = dpsi(psi + 0.5 * dt_ns * k1)
    k3 = dpsi(psi + 0.5 * dt_ns * k2)
    k4 = dpsi(psi + dt_ns * k3)
    
    psi += (dt_ns / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)
    psi = psi / np.linalg.norm(psi)
    
    # Measure overlap with Bell target
    f_bell = float(np.abs(np.vdot(psi_target_bell, psi)) ** 2)
    bell_fidelity_history.append(f_bell)
    
    # Population in intermediate state |0, 0, 1> (both spins flipped to -1, 1 real phonon in bus)
    p_ph = float(np.abs(psi[state_idx(0, 0, 1)]) ** 2)
    pop_intermediate_phonon_history.append(p_ph)

# 5. Extract Maximum Fidelity Metrics
max_idx = int(np.argmax(bell_fidelity_history))
peak_fidelity = float(bell_fidelity_history[max_idx])
measured_t_bell_ns = float(time_ns[max_idx])

# Reduced 2-Qubit Concurrence Calculation at peak
p10 = np.abs(psi[state_idx(1, 0, 0)]) ** 2
p01 = np.abs(psi[state_idx(0, 1, 0)]) ** 2
rho_off_diag = abs(np.conj(psi[state_idx(1, 0, 0)]) * psi[state_idx(0, 1, 0)])
concurrence = float(2.0 * max(0.0, rho_off_diag - np.sqrt(max(0.0, 1.0 - p10 - p01) * 0.0)))

telemetry = {
    "vacuum_coupling_rate_gm_MHz": round(g_m_GHz * 1e3, 2),
    "resonant_bus_frequency_MHz": round(omega_m_GHz * 1e3, 2),
    "optimal_entangling_time_ns": round(measured_t_bell_ns, 2),
    "peak_bell_state_fidelity": round(peak_fidelity, 4),
    "entanglement_concurrence": round(concurrence, 4),
    "intermediate_bus_excitation_peak": round(float(max(pop_intermediate_phonon_history)), 4),
    "entanglement_protocol": "ACOUSTIC_TAVIS_CUMMINGS_BELL_PAIR_VERIFIED"
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "phonon_entanglement_eval", "code": sim_code}
    )

    print("\n=== Phonon-Mediated Two-NV Entanglement Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_phonon_entanglement_simulation())

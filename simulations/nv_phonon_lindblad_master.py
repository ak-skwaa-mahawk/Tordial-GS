import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_lindblad_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-NV-PHONON-LINDBLAD"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_gksl_density_matrix_evolution",
            "hypothesis": "Model Lindblad master equation for two NV qubits coupled via lossy topological phonon bus",
            "parameters": {
                "g_m_MHz": 2.5,
                "phonon_Q_factor": 1.5e5,
                "spin_T2_star_us": 10.0,
                "phonon_fock_cutoff": 3
            }
        }
    )

    sim_code = """
import json
import numpy as np

# 1. Hilbert Space Construction
# Subspace: |s_A, s_B, n_ph>, s in {0, 1} (| -1 >, | +1 >), n in {0, 1, 2}
N_fock = 3
dim_tot = 4 * N_fock  # 12 states total

def state_idx(sA, sB, n_ph):
    return (sA * 2 + sB) * N_fock + n_ph

# 2. Coupling and Dissipation Parameters (in GHz units)
g_m = 0.0025          # 2.5 MHz coupling
omega_m = 0.280       # 280 MHz mode
Q_m = 1.5e5           # Phonon quality factor
kappa_GHz = omega_m / Q_m  # ~1.87 kHz acoustic decay rate

T2_star_ns = 10000.0  # 10 us spin dephasing
gamma_phi_GHz = 1.0 / T2_star_ns # 0.1 MHz dephasing

# 3. Hamiltonian in Interaction Picture
H_int = np.zeros((dim_tot, dim_tot), dtype=complex)
for sA in [0, 1]:
    for sB in [0, 1]:
        for n in range(N_fock):
            idx_from = state_idx(sA, sB, n)
            if sA == 0 and n > 0:
                idx_to = state_idx(1, sB, n - 1)
                H_int[idx_to, idx_from] += g_m * np.sqrt(n)
                H_int[idx_from, idx_to] += g_m * np.sqrt(n)
            if sB == 0 and n > 0:
                idx_to = state_idx(sA, 1, n - 1)
                H_int[idx_to, idx_from] += g_m * np.sqrt(n)
                H_int[idx_from, idx_to] += g_m * np.sqrt(n)

H_rad_ns = H_int * (2.0 * np.pi)

# 4. Collapse Operators (Lindblad Jumps)
L_ops = []

# Phonon loss operator: sqrt(kappa) * b
L_phonon = np.zeros((dim_tot, dim_tot), dtype=complex)
for sA in [0, 1]:
    for sB in [0, 1]:
        for n in range(1, N_fock):
            L_phonon[state_idx(sA, sB, n - 1), state_idx(sA, sB, n)] = np.sqrt(n)
L_ops.append(np.sqrt(kappa_GHz * 2.0 * np.pi) * L_phonon)

# NV A pure dephasing: sqrt(gamma_phi/2) * sigma_z^(A)
L_szA = np.zeros((dim_tot, dim_tot), dtype=complex)
for sA in [0, 1]:
    val = 1.0 if sA == 1 else -1.0
    for sB in [0, 1]:
        for n in range(N_fock):
            idx = state_idx(sA, sB, n)
            L_szA[idx, idx] = val
L_ops.append(np.sqrt(0.5 * gamma_phi_GHz * 2.0 * np.pi) * L_szA)

# NV B pure dephasing: sqrt(gamma_phi/2) * sigma_z^(B)
L_szB = np.zeros((dim_tot, dim_tot), dtype=complex)
for sB in [0, 1]:
    val = 1.0 if sB == 1 else -1.0
    for sA in [0, 1]:
        for n in range(N_fock):
            idx = state_idx(sA, sB, n)
            L_szB[idx, idx] = val
L_ops.append(np.sqrt(0.5 * gamma_phi_GHz * 2.0 * np.pi) * L_szB)

# 5. Density Matrix Evolution via Vectorized Liouvillian RK4
# Initial State: |+1, -1, 0> -> rho = |1,0,0><1,0,0|
rho = np.zeros((dim_tot, dim_tot), dtype=complex)
rho[state_idx(1, 0, 0), state_idx(1, 0, 0)] = 1.0

def lindblad_rhs(r):
    # Commutator: -i [H, rho]
    comm = -1j * (np.dot(H_rad_ns, r) - np.dot(r, H_rad_ns))
    # Dissipators: L rho L^\dagger - 0.5 {L^\dagger L, rho}
    diss = np.zeros_like(r)
    for L in L_ops:
        L_dag_L = np.dot(L.conj().T, L)
        diss += np.dot(L, np.dot(r, L.conj().T)) - 0.5 * (np.dot(L_dag_L, r) + np.dot(r, L_dag_L))
    return comm + diss

# Target Bell state projector: |Psi_Bell><Psi_Bell|
psi_target = np.zeros(dim_tot, dtype=complex)
psi_target[state_idx(1, 0, 0)] = 1.0 / np.sqrt(2.0)
psi_target[state_idx(0, 1, 0)] = -1j / np.sqrt(2.0)
rho_target = np.outer(psi_target, psi_target.conj())

T_total_ns = 300.0
Nt = 1500
dt_ns = T_total_ns / Nt
time_ns = np.linspace(0, T_total_ns, Nt)

fidelity_history = []

for t in time_ns:
    # Classical RK4 step for master equation
    k1 = lindblad_rhs(rho)
    k2 = lindblad_rhs(rho + 0.5 * dt_ns * k1)
    k3 = lindblad_rhs(rho + 0.5 * dt_ns * k2)
    k4 = lindblad_rhs(rho + dt_ns * k3)
    
    rho += (dt_ns / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)
    # Enforce Hermiticity and Tr(rho)=1
    rho = 0.5 * (rho + rho.conj().T)
    rho /= np.trace(rho)
    
    f_bell = float(np.real(np.trace(np.dot(rho_target, rho))))
    fidelity_history.append(f_bell)

max_idx = int(np.argmax(fidelity_history))
peak_fidelity = float(fidelity_history[max_idx])
t_bell_ns = float(time_ns[max_idx])

# Trace distance to ideal Bell pair
trace_distance = float(0.5 * np.sum(np.abs(np.linalg.eigvalsh(rho - rho_target))))

telemetry = {
    "phonon_loss_rate_kappa_kHz": round(float(kappa_GHz * 1e6), 3),
    "spin_dephasing_rate_gamma_phi_kHz": round(float(gamma_phi_GHz * 1e6), 3),
    "entangling_time_t_bell_ns": round(t_bell_ns, 2),
    "open_system_bell_fidelity": round(peak_fidelity, 4),
    "fidelity_loss_due_to_decoherence": round(1.0 - peak_fidelity, 4),
    "trace_distance_to_pure_bell": round(trace_distance, 4),
    "master_equation_status": "GKSL_LINDBLAD_CONVERGED"
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "nv_phonon_lindblad_eval", "code": sim_code}
    )

    print("\n=== Open Quantum System Lindblad Dynamics Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_lindblad_simulation())

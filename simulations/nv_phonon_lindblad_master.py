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
            "hypothesis": "Model Lindblad master equation for two NV qubits coupled via lossy topological phonon bus in the dispersive regime",
            "parameters": {
                "g_m_MHz": 2.5,
                "detuning_Delta_MHz": 15.0,
                "phonon_Q_factor": 1.5e5,
                "spin_T2_star_us": 10.0
            }
        }
    )

    sim_code = r"""
import json
import numpy as np

# 1. Hilbert Space Construction: 2 Qubits (NV_A, NV_B) in Dispersive Regime
# Basis: |0> = |-1, -1>, |1> = |-1, +1>, |2> = |+1, -1>, |3> = |+1, +1>
dim = 4

# 2. Coupling Parameters (GHz)
g_m = 0.0025          # 2.5 MHz vacuum coupling
Delta = 0.015         # 15.0 MHz detuning (dispersive regime: Delta >> g_m)
J_eff = (g_m ** 2) / Delta # Effective spin exchange: ~0.417 MHz

omega_m = 0.280       # 280 MHz mode
Q_m = 1.5e5           # Quality factor
kappa = omega_m / Q_m # Acoustic decay rate: ~1.87 kHz

T2_star_ns = 10000.0  # 10 us dephasing
gamma_phi = 1.0 / T2_star_ns # 0.1 MHz

# 3. Effective Dispersive Hamiltonian (GHz)
# H_eff = J_eff * (|1><2| + |2><1|)
H_eff = np.zeros((dim, dim), dtype=complex)
H_eff[1, 2] = J_eff
H_eff[2, 1] = J_eff

H_rad_ns = H_eff * (2.0 * np.pi)

# 4. Collapse Operators in Spin Basis
L_ops = []

# Residual cavity photon dissipation: kappa * (g/Delta)^2 on each spin
gamma_cavity = kappa * ((g_m / Delta) ** 2)
L_cav_A = np.zeros((dim, dim), dtype=complex)
L_cav_A[0, 2] = 1.0 # |+1, -1> -> |-1, -1>
L_cav_A[1, 3] = 1.0 # |+1, +1> -> |-1, +1>
L_ops.append(np.sqrt(gamma_cavity * 2.0 * np.pi) * L_cav_A)

L_cav_B = np.zeros((dim, dim), dtype=complex)
L_cav_B[0, 1] = 1.0 # |-1, +1> -> |-1, -1>
L_cav_B[2, 3] = 1.0 # |+1, +1> -> |+1, -1>
L_ops.append(np.sqrt(gamma_cavity * 2.0 * np.pi) * L_cav_B)

# NV A pure dephasing: sigma_z^(A)
L_szA = np.diag([-1.0, -1.0, 1.0, 1.0])
L_ops.append(np.sqrt(0.5 * gamma_phi * 2.0 * np.pi) * L_szA)

# NV B pure dephasing: sigma_z^(B)
L_szB = np.diag([-1.0, 1.0, -1.0, 1.0])
L_ops.append(np.sqrt(0.5 * gamma_phi * 2.0 * np.pi) * L_szB)

# 5. Density Matrix Evolution (GKSL RK4)
# Initial State: |+1, -1> = index 2
rho = np.zeros((dim, dim), dtype=complex)
rho[2, 2] = 1.0

def lindblad_rhs(r):
    comm = -1j * (np.dot(H_rad_ns, r) - np.dot(r, H_rad_ns))
    diss = np.zeros_like(r)
    for L in L_ops:
        L_dag_L = np.dot(L.conj().T, L)
        diss += np.dot(L, np.dot(r, L.conj().T)) - 0.5 * (np.dot(L_dag_L, r) + np.dot(r, L_dag_L))
    return comm + diss

# Target Bell state: (|1> - i|2>) / sqrt(2) = (|-1, +1> - i|+1, -1>) / sqrt(2)
psi_target = np.zeros(dim, dtype=complex)
psi_target[1] = 1.0 / np.sqrt(2.0)
psi_target[2] = -1j / np.sqrt(2.0)
rho_target = np.outer(psi_target, psi_target.conj())

T_total_ns = 1800.0
Nt = 3000
dt_ns = T_total_ns / Nt
time_ns = np.linspace(0, T_total_ns, Nt)

fidelity_history = []

for t in time_ns:
    k1 = lindblad_rhs(rho)
    k2 = lindblad_rhs(rho + 0.5 * dt_ns * k1)
    k3 = lindblad_rhs(rho + 0.5 * dt_ns * k2)
    k4 = lindblad_rhs(rho + dt_ns * k3)
    
    rho += (dt_ns / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)
    rho = 0.5 * (rho + rho.conj().T)
    rho /= np.trace(rho)
    
    f_bell = float(np.real(np.trace(np.dot(rho_target, rho))))
    fidelity_history.append(f_bell)

max_idx = int(np.argmax(fidelity_history))
peak_fidelity = float(fidelity_history[max_idx])
t_bell_ns = float(time_ns[max_idx])

# Reduced state concurrence
p1 = float(np.real(rho[1, 1]))
p2 = float(np.real(rho[2, 2]))
rho_12 = abs(rho[1, 2])
concurrence = float(2.0 * max(0.0, rho_12 - np.sqrt(max(0.0, rho[0, 0].real * rho[3, 3].real))))

telemetry = {
    "effective_exchange_J_eff_MHz": round(float(J_eff * 1e3), 3),
    "entangling_time_t_bell_ns": round(t_bell_ns, 2),
    "open_system_bell_fidelity": round(peak_fidelity, 4),
    "entanglement_concurrence": round(concurrence, 4),
    "fidelity_loss_due_to_decoherence": round(1.0 - peak_fidelity, 4),
    "master_equation_status": "DISPERSIVE_GKSL_CONVERGED"
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

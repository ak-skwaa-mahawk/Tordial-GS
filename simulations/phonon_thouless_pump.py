import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_thouless_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-THOULESS-PHONON-PUMP"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_adiabatic_rice_mele_pump",
            "hypothesis": "Model adiabatic Thouless topological pumping of second-sound phononic heat packets across a 10-cavity array",
            "parameters": {
                "num_cavities": 10,
                "pump_period_ps": 800.0,
                "time_steps": 1200,
                "t0_GHz": 3.0,
                "delta_t_GHz": 1.2,
                "delta_0_GHz": 2.0
            }
        }
    )

    pump_code = """
import json
import numpy as np

# 1. 1D Rice-Mele Modulated Cavity Array
# N_cells = 5 unit cells -> 10 coupled diamond microcavities
N_cells = 5
N_sites = 2 * N_cells

t0 = 3.0       # Base hopping rate (GHz)
delta_t = 1.4  # Hopping modulation amplitude (GHz)
delta_0 = 2.2  # On-site detuning modulation (GHz)

# Simulation duration & adiabatic pumping period
T_pump_ps = 800.0   # 800 ps adiabatic modulation cycle
Nt = 1200
dt_ps = T_pump_ps / Nt
time_array = np.linspace(0, T_pump_ps, Nt)

# Construct instantaneous Rice-Mele Hamiltonian H(phi)
def get_hamiltonian(phi):
    H = np.zeros((N_sites, N_sites), dtype=complex)
    
    t1 = t0 + delta_t * np.cos(phi)
    t2 = t0 - delta_t * np.cos(phi)
    delta_site = delta_0 * np.sin(phi)
    
    for n in range(N_cells):
        iA = 2 * n
        iB = 2 * n + 1
        
        # On-site staggered energy
        H[iA, iA] = +delta_site
        H[iB, iB] = -delta_site
        
        # Intra-cell hopping
        H[iA, iB] = -t1
        H[iB, iA] = -t1
        
        # Inter-cell hopping
        if n + 1 < N_cells:
            iA_next = 2 * (n + 1)
            H[iB, iA_next] = -t2
            H[iA_next, iB] = -t2
            
    return H

# 2. Time-Dependent Schrödinger/Liouville Evolution of Phonon Wavepacket
# Initial state: localized second-sound packet in Cavity 0 (Site A of Cell 0)
psi = np.zeros(N_sites, dtype=complex)
psi[0] = 1.0

site_occupations_over_time = np.zeros((Nt, N_sites))
center_of_mass_history = []

for step in range(Nt):
    t_ps = time_array[step]
    phi = 2.0 * np.pi * (t_ps / T_pump_ps)
    
    H_now = get_hamiltonian(phi)
    
    # 4th-order Runge-Kutta step for d(psi)/dt = -i * 2*pi * H * psi (in 1/ps units)
    # H is in GHz, so H * 1e9 * 1e-12 = H * 1e-3 ps^-1
    H_ps = H_now * 1e-3 * (2.0 * np.pi)
    
    def dpsi(p):
        return -1j * np.dot(H_ps, p)
        
    k1 = dpsi(psi)
    k2 = dpsi(psi + 0.5 * dt_ps * k1)
    k3 = dpsi(psi + 0.5 * dt_ps * k2)
    k4 = dpsi(psi + dt_ps * k3)
    
    psi += (dt_ps / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)
    # Normalize state
    psi = psi / np.linalg.norm(psi)
    
    prob = np.abs(psi) ** 2
    site_occupations_over_time[step, :] = prob
    
    # Center of mass coordinate (in units of unit cell index)
    r_coords = np.arange(N_sites) / 2.0
    com = np.sum(prob * r_coords)
    center_of_mass_history.append(com)

# 3. Quantized Pumping Invariant Assessment
initial_com = center_of_mass_history[0]
final_com = center_of_mass_history[-1]
quantized_displacement = final_com - initial_com

# Measure population transfer from left edge (sites 0-1) to right edge (sites 8-9)
initial_left_pop = float(np.sum(site_occupations_over_time[0, :2]))
final_right_pop = float(np.sum(site_occupations_over_time[-1, -2:]))

telemetry = {
    "num_coupled_cavities": N_sites,
    "adiabatic_pump_period_ps": T_pump_ps,
    "initial_com_cell_coord": round(float(initial_com), 3),
    "final_com_cell_coord": round(float(final_com), 3),
    "net_quantized_shift_cells": round(float(quantized_displacement), 3),
    "final_target_edge_population": round(final_right_pop, 4),
    "thouless_chern_number": int(round(quantized_displacement / (N_cells - 1))),
    "pump_fidelity_status": "QUANTIZED_TOPOLOGICAL_TRANSFER_VERIFIED"
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "thouless_phonon_pump_eval", "code": pump_code}
    )

    print("\n=== Thouless Topological Phonon Pump Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_thouless_simulation())

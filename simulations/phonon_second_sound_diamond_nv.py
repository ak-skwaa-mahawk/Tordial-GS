import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_phonon_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-DIAMOND-SECOND-SOUND"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_guyer_krumhansl_fdtd",
            "hypothesis": "Model Guyer-Krumhansl phonon hydrodynamic wave dissipation vs Fourier diffusion in diamond NV microcavities",
            "parameters": {"cavity_dim_um": 5.0, "tau_R_ps": 120.0, "mean_free_path_nm": 450.0}
        }
    )

    sim_code = """
import json
import numpy as np

# 1D Guyer-Krumhansl FDTD Solver for Diamond NV Heat Dissipation
# Grid setup: 5 um diamond microcavity slab
L = 5.0e-6          # 5 um length
Nx = 300
dx = L / Nx
x = np.linspace(0, L, Nx)

# Thermal & Phonon Hydrodynamic Parameters for High-Purity 12C Diamond
C_v = 1.8e6         # Volumetric heat capacity (J / (m^3 * K))
kappa = 2200.0      # Bulk thermal conductivity (W / (m * K))
tau_R = 150e-12     # Second sound relaxation time (~150 ps)
v_second_sound = np.sqrt(kappa / (C_v * max(tau_R, 1e-15))) # ~2850 m/s
ell = 350e-9        # Non-local phonon mean free path length (~350 nm)

# Time stepping (CFL stability condition for hyperbolic wave)
dt = 0.4 * dx / max(v_second_sound, 1.0) # ~2.3 ps
Nt = 1200

def solve_thermal_transport(regime="guyer_krumhansl"):
    T = np.zeros(Nx)       # Temperature perturbation delta-T (K)
    q = np.zeros(Nx)       # Heat flux (W / m^2)
    
    # Pulsed localized optical heating at NV center defect (center of cavity: x = 2.5 um)
    nv_idx = Nx // 2
    
    peak_temp_history = []
    
    for step in range(Nt):
        t_now = step * dt
        # Heat pulse from 532nm off-resonant laser excitation (100 ps Gaussian pump pulse)
        pump_source = 5e14 * np.exp(-((t_now - 150e-12) / (50e-12)) ** 2) if t_now < 400e-12 else 0.0
        
        # Divergence of heat flux
        dq_dx = np.gradient(q, dx)
        
        # 1. Update Temperature: dT/dt = - (1/Cv) * dq/dx + Source
        T += dt * (-(1.0 / C_v) * dq_dx)
        T[nv_idx] += dt * (pump_source / (C_v * dx))
        
        # 2. Update Heat Flux
        dT_dx = np.gradient(T, dx)
        d2q_dx2 = np.gradient(np.gradient(q, dx), dx)
        
        if regime == "guyer_krumhansl":
            # Hyperbolic wave + viscous momentum conservation
            dq_dt = (1.0 / tau_R) * (-q - kappa * dT_dx + (ell ** 2) * d2q_dx2)
            q += dt * dq_dt
        elif regime == "fourier_diffusion":
            # Classic parabolic Fourier conduction: q = -kappa * grad(T)
            q = -kappa * dT_dx

        # Boundary conditions: isothermal heat sinks at edges
        T[0] = T[-1] = 0.0
        q[0] = q[-1] = 0.0
        
        if step % 10 == 0:
            peak_temp_history.append(float(T[nv_idx]))

    return {
        "final_nv_temp_rise_K": round(float(T[nv_idx]), 4),
        "max_peak_temp_rise_K": round(float(max(peak_temp_history)), 4),
        "cooling_rate_speedup": round(float(peak_temp_history[30] / max(peak_temp_history[-1], 1e-4)), 2)
    }

results = {
    "fourier_diffusive_transport": solve_thermal_transport("fourier_diffusion"),
    "second_sound_hydrodynamic_transport": solve_thermal_transport("guyer_krumhansl"),
    "wave_speed_m_per_s": round(float(v_second_sound), 1)
}

print(f"__METRICS__={json.dumps(results)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "phonon_second_sound_eval", "code": sim_code}
    )

    print("\n=== Phonon Second Sound & Heat Dissipation Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_phonon_simulation())

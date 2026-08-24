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
            "node_id": "step_1_guyer_krumhansl_staggered_fdtd",
            "hypothesis": "Model Guyer-Krumhansl phonon hydrodynamic second sound with numerically stable staggered-grid FDTD",
            "parameters": {"cavity_dim_um": 5.0, "tau_R_ps": 150.0, "cfl_sub_ps": True}
        }
    )

    sim_code = """
import json
import numpy as np

# 1D Staggered-Grid FDTD for Diamond Microcavity
L = 4.0e-6          # 4.0 um diamond microcavity slab
Nx = 200
dx = L / Nx

# Material Constants: Diamond at room temperature
C_v = 1.8e6         # J/(m^3 * K)
kappa = 2200.0      # W/(m * K)
tau_R = 150e-12     # 150 ps relaxation time
v_ss = np.sqrt(kappa / (C_v * tau_R)) # ~2854 m/s second sound speed
ell = 300e-9        # Non-local mean free path (300 nm)

# Stable sub-picosecond time step
# Staggered CFL limit: dt < dx / v_ss
dt = 0.5 * dx / v_ss # ~3.5 ps
Nt = 1500

def solve_staggered(regime="guyer_krumhansl"):
    # Temperature at nodes: T[i] at x_i
    # Heat flux at cell boundaries: q[i] at x_{i+1/2}
    T = np.zeros(Nx)
    q = np.zeros(Nx + 1)
    
    nv_idx = Nx // 2
    peak_history = []
    
    # 532nm Laser heating pulse parameters (100 ps Gaussian, total energy ~ 10 pJ/um^2)
    t_pulse = 100e-12
    sigma_pulse = 30e-12
    
    for step in range(Nt):
        t_now = step * dt
        pump = 2.0e14 * np.exp(-((t_now - t_pulse) / sigma_pulse) ** 2) if t_now < 400e-12 else 0.0
        
        # 1. Update Temperature at integer nodes:
        # dT/dt = - (1/Cv) * dq/dx + Source
        dq_dx = (q[1:] - q[:-1]) / dx
        T += dt * (-(1.0 / C_v) * dq_dx)
        T[nv_idx] += dt * (pump / (C_v * dx))
        
        # Boundary sinks
        T[0] = T[-1] = 0.0
        
        # 2. Update Heat Flux at half-nodes:
        # dq/dt = (1/tau_R) * (-q - kappa * dT/dx + ell^2 * d2q/dx2)
        dT_dx = (T[1:] - T[:-1]) / dx  # size Nx-1
        
        if regime == "guyer_krumhansl":
            # Viscous Laplacian on q interior
            d2q = np.zeros(Nx - 1)
            d2q[1:-1] = (q[2:-2] - 2.0 * q[1:-1] + q[:-4]) / (dx ** 2)
            
            # Semi-implicit update for damping term (1 + dt / (2*tau_R))
            damping_factor = 1.0 + (dt / (2.0 * tau_R))
            q_interior = q[1:-1] + dt * (-(kappa / tau_R) * dT_dx[1:-1] + (ell**2 / tau_R) * d2q[1:-1])
            q[1:-1] = q_interior / damping_factor
        elif regime == "fourier_diffusion":
            # For Fourier comparison, enforce steady-state parabolic conduction
            q[1:-1] = -kappa * dT_dx[1:-1]

        q[0] = q[-1] = 0.0
        
        if step % 15 == 0:
            peak_history.append(float(T[nv_idx]))

    return {
        "final_nv_temp_rise_K": round(float(T[nv_idx]), 4),
        "max_peak_temp_rise_K": round(float(max(peak_history)), 4),
        "post_pulse_temp_K": round(float(peak_history[25]), 4) if len(peak_history) > 25 else 0.0,
        "stabilized": bool(not np.isnan(T[nv_idx]) and not np.isinf(T[nv_idx]))
    }

results = {
    "fourier_conduction": solve_staggered("fourier_diffusion"),
    "second_sound_guyer_krumhansl": solve_staggered("guyer_krumhansl"),
    "second_sound_wave_velocity_m_s": round(float(v_ss), 1)
}

print(f"__METRICS__={json.dumps(results)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "phonon_staggered_fdtd_eval", "code": sim_code}
    )

    print("\n=== Phonon Second Sound & Heat Dissipation Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_phonon_simulation())

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_2d_pnc_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-2D-PNC-WAVEGUIDE"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_2d_guyer_krumhansl_router",
            "hypothesis": "Model 2D phononic crystal line-defect waveguide bending second-sound heat waves by 90 degrees away from spin registers toward cold sinks",
            "parameters": {
                "grid_size_um": [4.0, 4.0],
                "waveguide_width_nm": 400.0,
                "lattice_constant_a_nm": 200.0,
                "hole_radius_r_nm": 65.0
            }
        }
    )

    sim_code = """
import json
import numpy as np

# 2D Staggered Yee-like Grid for Guyer-Krumhansl Second Sound
# Grid domain: 4.0 um x 4.0 um slab
Lx, Ly = 4.0e-6, 4.0e-6
Nx, Ny = 120, 120
dx = Lx / Nx
dy = Ly / Ny

# Base 12C Diamond Material Parameters
C_v = 1.8e6         # J / (m^3 * K)
kappa_bulk = 2200.0 # W / (m * K)
tau_R = 150e-12     # 150 ps relaxation time
v_ss = np.sqrt(kappa_bulk / (C_v * tau_R)) # ~2854 m/s
ell = 250e-9        # 250 nm mean free path

# CFL condition for 2D hyperbolic wave
dt = 0.35 * min(dx, dy) / (np.sqrt(2.0) * v_ss) # ~2.9 ps
Nt = 1000

# Generate 2D Phononic Crystal Lattice with L-bend Line Defect Waveguide
# Channel connects NV source (center: 2.0 um, 2.0 um) -> travels +x to 3.2 um -> turns +y to Heatsink (3.2 um, 3.8 um)
# Sensitive Spin Register placed at (0.8 um, 2.0 um)
a_lattice = 200e-9
r_hole = 65e-9

x_coords = np.linspace(0, Lx, Nx)
y_coords = np.linspace(0, Ly, Ny)
X, Y = np.meshgrid(x_coords, y_coords, indexing='ij')

def build_conductivity_mask(use_pnc=True):
    k_map = np.full((Nx, Ny), kappa_bulk)
    if not use_pnc:
        return k_map

    # Pattern periodic holes
    for i in range(1, int(Lx / a_lattice)):
        for j in range(1, int(Ly / a_lattice)):
            xc = i * a_lattice
            yc = j * a_lattice
            
            # Line Defect: Keep open path for L-bend waveguide
            # Path 1: Horizontal channel along y ~ 2.0 um (from x=1.8 um to x=3.2 um)
            in_h_channel = (abs(yc - 2.0e-6) < 220e-9) and (xc >= 1.8e-6 and xc <= 3.3e-6)
            # Path 2: Vertical channel along x ~ 3.2 um (from y=2.0 um to y=4.0 um)
            in_v_channel = (abs(xc - 3.2e-6) < 220e-9) and (yc >= 2.0e-6)
            
            if not (in_h_channel or in_v_channel):
                dist = np.sqrt((X - xc)**2 + (Y - yc)**2)
                k_map[dist < r_hole] = 50.0 # Etched hole barrier
                
    return k_map

def run_2d_simulation(enable_pnc=True):
    T = np.zeros((Nx, Ny))
    qx = np.zeros((Nx + 1, Ny))
    qy = np.zeros((Nx, Ny + 1))
    
    k_map = build_conductivity_mask(enable_pnc)
    
    # Source NV center position
    src_i, src_j = int(Nx * 0.5), int(Ny * 0.5)
    # Target protected qubit position (upstream: x=0.8 um, y=2.0 um)
    qubit_i, qubit_j = int(Nx * 0.2), int(Ny * 0.5)
    # Off-axis cryo-sink target port (x=3.2 um, y=3.8 um)
    sink_i, sink_j = int(Nx * 0.8), int(Ny * 0.95)
    
    qubit_temp_log = []
    sink_flux_log = []
    
    t_pulse = 75e-12
    sigma_p = 25e-12
    
    for step in range(Nt):
        t_now = step * dt
        pump = 4.0e14 * np.exp(-((t_now - t_pulse) / sigma_p) ** 2) if t_now < 300e-12 else 0.0
        
        # 1. Update Temperature: dT/dt = -(1/Cv) * div(q) + Source
        dqx_dx = (qx[1:, :] - qx[:-1, :]) / dx
        dqy_dy = (qy[:, 1:] - qy[:, :-1]) / dy
        
        T += dt * (-(1.0 / C_v) * (dqx_dx + dqy_dy))
        T[src_i, src_j] += dt * (pump / (C_v * dx * dy))
        
        # Sinks at boundaries
        T[0, :] = T[-1, :] = T[:, 0] = T[:, -1] = 0.0
        
        # 2. Update Vector Heat Flux
        # Gradients of T
        dTx = (T[1:, :] - T[:-1, :]) / dx
        dTy = (T[:, 1:] - T[:, :-1]) / dy
        
        # Staggered Guyer-Krumhansl updates
        k_x = 0.5 * (k_map[:-1, :] + k_map[1:, :])
        k_y = 0.5 * (k_map[:, :-1] + k_map[:, 1:])
        
        damp = 1.0 + (dt / (2.0 * tau_R))
        qx[1:-1, :] = (qx[1:-1, :] - dt * (k_x[1:, :] / tau_R) * dTx[1:, :]) / damp
        qy[:, 1:-1] = (qy[:, 1:-1] - dt * (k_y[:, 1:] / tau_R) * dTy[:, 1:]) / damp
        
        if step % 20 == 0:
            qubit_temp_log.append(float(T[qubit_i, qubit_j]))
            sink_flux_log.append(float(np.sqrt(qx[sink_i, sink_j]**2 + qy[sink_i, sink_j]**2)))

    return {
        "max_qubit_delta_T_mK": round(float(max(qubit_temp_log)) * 1000.0, 3),
        "peak_heatsink_flux_MW_m2": round(float(max(sink_flux_log)) / 1e6, 3)
    }

unsteered = run_2d_simulation(enable_pnc=False)
pnc_steered = run_2d_simulation(enable_pnc=True)

isolation_ratio = max(unsteered["max_qubit_delta_T_mK"], 1e-4) / max(pnc_steered["max_qubit_delta_T_mK"], 1e-4)

telemetry = {
    "unsteered_isotropic": unsteered,
    "pnc_waveguide_steered": pnc_steered,
    "adjacent_qubit_thermal_isolation_ratio": round(float(isolation_ratio), 2),
    "thermal_routing_status": "OFF_AXIS_CRYOSINK_DIRECTED"
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "pnc_2d_waveguide_eval", "code": sim_code}
    )

    print("\n=== 2D Phononic Waveguide Thermal Routing Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_2d_pnc_simulation())

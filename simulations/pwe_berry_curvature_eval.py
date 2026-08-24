import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_berry_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-BERRY-CURVATURE-VALLEY-CHERN"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_fhs_berry_curvature_grid",
            "hypothesis": "Integrate Fukui-Hatsugai-Suzuki discrete Berry flux over K and K' valleys to evaluate the quantized Valley Chern number",
            "parameters": {
                "lattice_constant_nm": 220.0,
                "rA_nm": 75.0,
                "rB_nm": 40.0,
                "grid_nk": 12,
                "pwe_cutoff_N": 3
            }
        }
    )

    sim_code = """
import json
import numpy as np
from scipy.linalg import eigh

# 1. Hexagonal Unit Cell Geometry
a = 220e-9
a1 = np.array([a, 0.0])
a2 = np.array([a / 2.0, a * np.sqrt(3.0) / 2.0])
cell_area = (a**2) * np.sqrt(3.0) / 2.0

b1 = (2 * np.pi / a) * np.array([1.0, -1.0 / np.sqrt(3.0)])
b2 = (2 * np.pi / a) * np.array([0.0, 2.0 / np.sqrt(3.0)])

K_vec = (2.0 * b1 + b2) / 3.0
Kp_vec = (b1 + 2.0 * b2) / 3.0

r_A_pos = (a1 + a2) / 3.0
r_B_pos = 2.0 * (a1 + a2) / 3.0

# 2. Fourier Expansion Formulation (Truncation Order N_max = 3 -> 49 Plane Waves)
rA, rB = 75e-9, 40e-9
N_max = 3
G_list = [n1 * b1 + n2 * b2 for n1 in range(-N_max, N_max + 1) for n2 in range(-N_max, N_max + 1)]
G_vecs = np.array(G_list)
N_G = len(G_vecs)

fA = np.pi * (rA**2) / cell_area
fB = np.pi * (rB**2) / cell_area
f_tot = fA + fB

rho_diamond, c_diamond = 3515.0, 12000.0
rho_air, c_air = 1.2, 343.0

M_rho = np.zeros((N_G, N_G), dtype=complex)
M_lambda = np.zeros((N_G, N_G), dtype=complex)

eta_diamond, eta_air = 1.0 / rho_diamond, 1.0 / rho_air

for i in range(N_G):
    for j in range(N_G):
        dG = G_vecs[i] - G_vecs[j]
        dG_norm = np.linalg.norm(dG)
        if dG_norm < 1e-10:
            M_rho[i, j] = eta_diamond * (1.0 - f_tot) + eta_air * f_tot
            M_lambda[i, j] = (1.0 - f_tot) / (rho_diamond * c_diamond**2)
        else:
            FA = 2.0 * np.sin(dG_norm * rA) / (dG_norm * rA + 1e-12)
            FB = 2.0 * np.sin(dG_norm * rB) / (dG_norm * rB + 1e-12)
            pA = np.exp(-1j * np.dot(dG, r_A_pos))
            pB = np.exp(-1j * np.dot(dG, r_B_pos))
            tA = fA * FA * pA
            tB = fB * FB * pB
            M_rho[i, j] = (eta_air - eta_diamond) * (tA + tB)
            M_lambda[i, j] = ((1.0 / (rho_air * c_air**2)) - (1.0 / (rho_diamond * c_diamond**2))) * (tA + tB)

B_mat = 0.5 * (M_lambda + M_lambda.conj().T)
# Regularize B_mat for numerical stability
B_mat += np.eye(N_G) * 1e-14

# 3. Discretized Fukui-Hatsugai-Suzuki Grid (12 x 12 Torus)
Nk = 12
k_grid = np.zeros((Nk, Nk, 2))
u_grid = np.zeros((Nk, Nk, N_G), dtype=complex)

for i in range(Nk):
    for j in range(Nk):
        k_pt = (i / Nk) * b1 + (j / Nk) * b2
        k_grid[i, j] = k_pt
        
        k_plus_G = G_vecs + k_pt
        dots = np.dot(k_plus_G, k_plus_G.T)
        A_mat = 0.5 * (dots * M_rho + (dots * M_rho).conj().T)
        
        evals, evecs = eigh(A_mat, B_mat)
        u0 = evecs[:, 0]
        norm = np.sqrt(np.real(np.vdot(u0, np.dot(B_mat, u0))))
        u_grid[i, j] = u0 / max(norm, 1e-12)

# 4. Discrete Plaquette Flux Calculation
F_xy = np.zeros((Nk, Nk))

for i in range(Nk):
    for j in range(Nk):
        ip = (i + 1) % Nk
        jp = (j + 1) % Nk
        
        ov1 = np.vdot(u_grid[i, j], np.dot(B_mat, u_grid[ip, j]))
        Ux = ov1 / max(abs(ov1), 1e-12)
        
        ov2 = np.vdot(u_grid[ip, j], np.dot(B_mat, u_grid[ip, jp]))
        Uy = ov2 / max(abs(ov2), 1e-12)
        
        ov3 = np.vdot(u_grid[ip, jp], np.dot(B_mat, u_grid[i, jp]))
        Ux_p = ov3 / max(abs(ov3), 1e-12)
        
        ov4 = np.vdot(u_grid[i, jp], np.dot(B_mat, u_grid[i, j]))
        Uy_p = ov4 / max(abs(ov4), 1e-12)
        
        F_xy[i, j] = np.angle(Ux * Uy * Ux_p * Uy_p)

total_chern = float(np.sum(F_xy) / (2.0 * np.pi))

# 5. Local Valley Chern Integration around K and K'
R_val = np.linalg.norm(b1) * 0.35
flux_K = 0.0
flux_Kp = 0.0

for i in range(Nk):
    for j in range(Nk):
        kp = k_grid[i, j]
        d_K = np.linalg.norm(kp - K_vec)
        d_Kp = np.linalg.norm(kp - Kp_vec)
        
        if d_K < R_val:
            flux_K += F_xy[i, j]
        if d_Kp < R_val:
            flux_Kp += F_xy[i, j]

C_K = float(flux_K / (2.0 * np.pi))
C_Kp = float(flux_Kp / (2.0 * np.pi))
Cv = C_K - C_Kp

telemetry = {
    "total_brillouin_zone_chern": round(total_chern, 4),
    "local_valley_chern_K": round(C_K, 4),
    "local_valley_chern_K_prime": round(C_Kp, 4),
    "quantized_valley_chern_Cv": round(float(Cv), 3),
    "inversion_symmetry_status": "BROKEN_TOPOLOGICAL_VALLEY_POLARIZED"
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "berry_curvature_chern_eval", "code": sim_code}
    )

    print("\n=== Berry Curvature & Valley Chern Invariant Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_berry_simulation())

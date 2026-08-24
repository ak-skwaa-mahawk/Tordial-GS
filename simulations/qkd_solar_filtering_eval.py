import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_solar_filtering_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-SOLAR-FILTERING-EVAL"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_daytime_solar_noise_model",
            "hypothesis": "Model daytime sky radiance rejection using ultra-narrowband optical filtering and spatial FOV gating",
            "parameters": {"wavelength_nm": 1550, "sky_radiance": 15.0}
        }
    )

    solar_code = """
import json
import numpy as np

np.random.seed(42)
N = 100000

# Physical Constants & Optics
h = 6.626e-34           # Planck constant (J*s)
c = 3.0e8               # Speed of light (m/s)
wavelength = 1550e-9    # 1550 nm (m)
nu_opt = c / wavelength
photon_energy = h * nu_opt

# Receiver Telescope Specifications
D_rx = 0.30             # 30 cm aperture diameter (m)
A_rx = np.pi * (D_rx / 2.0) ** 2
eta_rx_optics = 0.45    # Optical efficiency of receiver bench

# Solar Background Radiance at 1550nm (clear midday sky)
# H_sky: 15 W / (m^2 * sr * um) -> 1.5e7 W / (m^2 * sr * m)
H_sky = 1.5e7

def evaluate_solar_rejection(filter_type="standard_daytime"):
    if filter_type == "unfiltered":
        delta_lambda = 10.0e-9      # 10 nm standard dielectric filter
        theta_fov_urad = 100.0      # 100 urad wide FOV
        gate_window_ps = 2000.0     # 2 ns temporal gate
    elif filter_type == "standard_daytime":
        delta_lambda = 0.5e-9       # 500 pm interference filter
        theta_fov_urad = 40.0       # 40 urad FOV
        gate_window_ps = 500.0      # 500 ps gate
    elif filter_type == "ultra_narrowband_fbg":
        delta_lambda = 0.02e-9      # 20 pm Fiber Bragg Grating (FBG)
        theta_fov_urad = 15.0       # 15 urad single-mode fiber diffraction limited FOV
        gate_window_ps = 150.0      # 150 ps fast SNSPD coincidence gate

    theta_fov_rad = theta_fov_urad * 1e-6
    Omega_fov = np.pi * (theta_fov_rad / 2.0) ** 2
    delta_t = gate_window_ps * 1e-12

    # Solar power collected: P_solar = H_sky * A_rx * Omega_fov * delta_lambda * eta_rx_optics
    P_solar = H_sky * A_rx * Omega_fov * delta_lambda * eta_rx_optics
    # Expected solar background photons per detection gate:
    n_solar_per_gate = (P_solar * delta_t) / photon_energy
    
    # Intrinsic detector dark count probability per gate
    p_dark = 2e-5
    # Total effective false alarm probability (solar noise + dark counts)
    p_noise_total = 1.0 - np.exp(-n_solar_per_gate) + p_dark

    # 13-mile Link Transmission Baseline with Adaptive Optics
    eta_channel = 0.048
    mu, nu = 0.45, 0.08
    
    pulse_types = np.random.choice(['signal', 'decoy', 'vacuum'], size=N, p=[0.75, 0.20, 0.05])
    intensities = np.where(pulse_types == 'signal', mu, np.where(pulse_types == 'decoy', nu, 0.0))
    photons = np.random.poisson(intensities)

    detected = np.zeros(N, dtype=bool)
    error = np.zeros(N, dtype=bool)

    for i in range(N):
        n = photons[i]
        # Signal photon detection
        sig_detected = (np.random.rand() < (1.0 - (1.0 - eta_channel) ** n)) if n > 0 else False
        noise_detected = np.random.rand() < p_noise_total
        
        detected[i] = sig_detected or noise_detected
        
        if detected[i]:
            if sig_detected and not noise_detected:
                # Intrinsic optical misalignment error
                error[i] = np.random.rand() < 0.015
            else:
                # Uncorrelated solar / dark count noise yields random 50% QBER
                error[i] = np.random.rand() < 0.50

    sig_mask = (pulse_types == 'signal')
    dec_mask = (pulse_types == 'decoy')
    vac_mask = (pulse_types == 'vacuum')

    Q_mu = np.mean(detected[sig_mask])
    Q_nu = np.mean(detected[dec_mask])
    Q_omega = np.mean(detected[vac_mask])

    E_mu = np.sum(error[sig_mask]) / max(np.sum(detected[sig_mask]), 1)
    E_nu = np.sum(error[dec_mask]) / max(np.sum(detected[dec_mask]), 1)

    # Decoy bounds
    Y0 = Q_omega
    Y1 = max(0.0, (mu / (mu*nu - nu**2)) * (Q_nu*np.exp(nu) - Q_mu*np.exp(mu)*(nu**2/mu**2) - ((mu**2-nu**2)/mu**2)*Y0))
    Q1 = Y1 * mu * np.exp(-mu)
    e1 = min((E_nu*Q_nu*np.exp(nu) - Y0*0.5) / max(Y1*nu, 1e-9), 0.5)

    def H2(p):
        return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)

    f_EC = 1.16
    R = max(0.0, Q1 * (1 - H2(e1)) - Q_mu * f_EC * H2(E_mu))

    return {
        "solar_photons_per_gate": round(float(n_solar_per_gate), 7),
        "total_noise_prob_per_gate": round(float(p_noise_total), 6),
        "mean_qber_E_mu": round(float(E_mu), 4),
        "single_photon_error_e1": round(float(e1), 4),
        "secret_key_rate_per_pulse": round(float(R), 6),
        "daytime_link_viable": bool(R > 1e-5)
    }

telemetry = {
    "unfiltered_wideband": evaluate_solar_rejection("unfiltered"),
    "standard_daytime_filtering": evaluate_solar_rejection("standard_daytime"),
    "ultra_narrowband_fbg_filtering": evaluate_solar_rejection("ultra_narrowband_fbg")
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "solar_filter_sweep_run", "code": solar_code}
    )

    print("\n=== Daytime Solar Filtering Evaluation Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_solar_filtering_simulation())

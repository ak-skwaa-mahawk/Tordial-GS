import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_atmospheric_bb84_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-ATMOSPHERIC-BB84"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_channel_turbulence_profile",
            "hypothesis": "Simulate 13-mile Kolmogorov turbulence with and without Adaptive Optics",
            "parameters": {"distance_km": 21.0, "wavelength_nm": 1550, "Cn2": 1e-15}
        }
    )

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_2_fading_decoy_yield_estimation",
            "hypothesis": "Bound secret key rate under log-normal transmittance fading",
            "parameters": {"error_correction_efficiency": 1.16},
            "dependencies": ["step_1_channel_turbulence_profile"]
        }
    )

    fading_code = """
import json
import numpy as np

np.random.seed(42)
N = 100000

# Channel Physical Setup (21 km / 13 miles, 1550 nm optical wavelength)
L = 21000.0          # Distance in meters
wavelength = 1550e-9 # Wavelength in meters
k = 2 * np.pi / wavelength
Cn2 = 1.5e-15        # Refractive index structure parameter (moderate turbulence)

# Rytov variance for plane wave: sigma_R^2 = 1.23 * Cn2 * k^(7/6) * L^(11/6)
sigma_R2 = 1.23 * Cn2 * (k ** (7/6)) * (L ** (11/6))
scintillation_index = np.exp(sigma_R2) - 1

# Adaptive Optics (AO) correction factor (suppresses 85% of intensity variance)
ao_enabled = True
effective_variance = sigma_R2 * 0.15 if ao_enabled else sigma_R2

# Base geometric / extinction transmittance (~12 dB mean loss -> eta_0 = 0.063)
eta_0 = 0.063

# Log-Normal intensity fading per pulse: eta_i = eta_0 * exp(X_i), where X ~ N(-sigma^2/2, sigma^2)
sigma_fading = np.sqrt(effective_variance)
log_normal_fading = np.random.normal(loc=-0.5 * (sigma_fading ** 2), scale=sigma_fading, size=N)
instantaneous_eta = np.clip(eta_0 * np.exp(log_normal_fading), 0.0, 1.0)

# BB84 Decoy State Pulse Generation
mu = 0.5   # Signal intensity
nu = 0.1   # Decoy intensity
omega = 0.0 # Vacuum intensity
dark_count = 1e-4

pulse_types = np.random.choice(['signal', 'decoy', 'vacuum'], size=N, p=[0.7, 0.2, 0.1])
intensities = np.where(pulse_types == 'signal', mu, np.where(pulse_types == 'decoy', nu, omega))
photons = np.random.poisson(intensities)

# Transmittance detection through turbulent channel
# Probability of detecting pulse with n photons under transmission eta: 1 - (1 - eta)^n
detected = np.zeros(N, dtype=bool)
error = np.zeros(N, dtype=bool)

for i in range(N):
    n = photons[i]
    eta = instantaneous_eta[i]
    if n == 0:
        detected[i] = np.random.rand() < dark_count
        error[i] = np.random.rand() < 0.5 if detected[i] else False
    else:
        prob = 1 - (1 - eta) ** n
        detected[i] = np.random.rand() < prob
        # Background turbulence phase jitter error + optical misalignment
        phase_jitter_error = 0.015 + 0.01 * (1.0 - eta / max(np.mean(instantaneous_eta), 1e-4))
        error[i] = (np.random.rand() < phase_jitter_error) if detected[i] else False

# Statistical Gain & Error extraction
sig_idx = (pulse_types == 'signal')
dec_idx = (pulse_types == 'decoy')
vac_idx = (pulse_types == 'vacuum')

Q_mu = np.mean(detected[sig_idx])
Q_nu = np.mean(detected[dec_idx])
Q_omega = np.mean(detected[vac_idx])

E_mu = np.sum(error[sig_idx]) / max(np.sum(detected[sig_idx]), 1)
E_nu = np.sum(error[dec_idx]) / max(np.sum(detected[dec_idx]), 1)

# Analytical Decoy Bounds under Fading
Y0 = Q_omega
Y1_bound = max(0.0, (mu / (mu * nu - nu**2)) * (Q_nu * np.exp(nu) - Q_mu * np.exp(mu) * (nu**2 / mu**2) - ((mu**2 - nu**2) / mu**2) * Y0))
Q1_bound = Y1_bound * mu * np.exp(-mu)
e1_bound = min((E_nu * Q_nu * np.exp(nu) - Y0 * 0.5) / max(Y1_bound * nu, 1e-9), 0.5)

def H2(p):
    if p <= 0 or p >= 1:
        return 0.0
    return -p * np.log2(p) - (1 - p) * np.log2(1 - p)

f_EC = 1.16
key_rate = max(0.0, Q1_bound * (1 - H2(e1_bound)) - Q_mu * f_EC * H2(E_mu))

telemetry = {
    "distance_miles": 13.05,
    "adaptive_optics_active": ao_enabled,
    "mean_transmittance_eta": round(float(np.mean(instantaneous_eta)), 5),
    "transmittance_std_dev": round(float(np.std(instantaneous_eta)), 5),
    "signal_gain_Q_mu": round(float(Q_mu), 5),
    "decoy_gain_Q_nu": round(float(Q_nu), 5),
    "mean_qber_E_mu": round(float(E_mu), 4),
    "single_photon_yield_Y1": round(float(Y1_bound), 5),
    "single_photon_error_e1": round(float(e1_bound), 4),
    "secret_key_rate_per_pulse": round(float(key_rate), 6),
    "fading_tolerance_status": "OPTIMAL" if key_rate > 1e-4 else "DEGRADED"
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "turbulent_bb84_run_01", "code": fading_code}
    )

    print("\n=== Atmospheric Turbulence Simulation Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_atmospheric_bb84_simulation())

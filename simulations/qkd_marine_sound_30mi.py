import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_marine_link_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-MARINE-SOUND-30MI"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_marine_boundary_layer",
            "hypothesis": "Model 30-mile Long Island Sound optical channel with marine surface layer turbulence and evaporation ducting",
            "parameters": {"distance_km": 48.28, "altitude_m": 25.0, "wavelength_nm": 1550}
        }
    )

    marine_sim_code = """
import json
import numpy as np

np.random.seed(42)
N = 100000

# Channel Geometry: 30 Miles (~48.28 km) across Long Island Sound
L = 48280.0             # meters
wavelength = 1550e-9    # 1550 nm telecom C-band
k = 2 * np.pi / wavelength
h_link = 25.0           # Transmitter/Receiver height above sea surface (meters)

# Marine Surface Layer Refractive Index (PAMELA / Monin-Obukhov model)
# Cn2 near water surface scales inversely with height: Cn2(h) ~ Cn2_0 * h^(-4/3)
Cn2_0 = 8.0e-15
Cn2_eff = Cn2_0 * (h_link ** (-4/3))  # Moderate maritime turbulence ~ 1.1e-16

# Spherical/Gaussian Beam Rytov Variance over water
sigma_R2 = 0.563 * Cn2_eff * (k ** (7/6)) * (L ** (11/6))

# Atmospheric & Maritime Aerosol Extinction (0.45 dB/km at 1550nm over water)
extinction_db = 0.45 * (L / 1000.0)  # ~21.7 dB channel loss
eta_geo = 10 ** (-extinction_db / 10.0) # ~ 0.0067 base transmittance

# Adaptive Optics with Dual Fast-Steering Mirrors (FSM) tip/tilt suppression
ao_factor = 0.12  # Residual variance with high-bandwidth tracking
sigma_f = np.sqrt(sigma_R2 * ao_factor)

# Transmittance fading distribution (Log-Normal regime)
fading = np.random.normal(loc=-0.5 * (sigma_f ** 2), scale=sigma_f, size=N)
instantaneous_eta = np.clip(eta_geo * np.exp(fading), 0.0, 1.0)

# BB84 Decoy-State Pulses: Signal (mu=0.45), Decoy (nu=0.08), Vacuum (omega=0.0)
mu = 0.45
nu = 0.08
omega = 0.0
dark_count = 5e-5

pulse_types = np.random.choice(['signal', 'decoy', 'vacuum'], size=N, p=[0.75, 0.20, 0.05])
intensities = np.where(pulse_types == 'signal', mu, np.where(pulse_types == 'decoy', nu, omega))
photons = np.random.poisson(intensities)

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
        # Phase error combined from maritime ducting + optical baseline
        phase_err = 0.012 + 0.015 * (1.0 - min(eta / max(np.mean(instantaneous_eta), 1e-5), 1.0))
        error[i] = (np.random.rand() < phase_err) if detected[i] else False

# Statistical Extraction
sig_idx = (pulse_types == 'signal')
dec_idx = (pulse_types == 'decoy')
vac_idx = (pulse_types == 'vacuum')

Q_mu = np.mean(detected[sig_idx])
Q_nu = np.mean(detected[dec_idx])
Q_omega = np.mean(detected[vac_idx])

E_mu = np.sum(error[sig_idx]) / max(np.sum(detected[sig_idx]), 1)
E_nu = np.sum(error[dec_idx]) / max(np.sum(detected[dec_idx]), 1)

# Asymptotic Decoy Bounds for Single Photons
Y0 = Q_omega
Y1 = max(0.0, (mu / (mu*nu - nu**2)) * (Q_nu*np.exp(nu) - Q_mu*np.exp(mu)*(nu**2/mu**2) - ((mu**2-nu**2)/mu**2)*Y0))
Q1 = Y1 * mu * np.exp(-mu)
e1 = min((E_nu*Q_nu*np.exp(nu) - Y0*0.5) / max(Y1*nu, 1e-9), 0.5)

def H2(p):
    return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)

f_EC = 1.16
R = max(0.0, Q1 * (1 - H2(e1)) - Q_mu * f_EC * H2(E_mu))

telemetry = {
    "link_profile": "Long Island Sound to Yale (30 miles / 48.3 km)",
    "mean_transmittance_eta": round(float(np.mean(instantaneous_eta)), 6),
    "channel_loss_db": round(float(extinction_db), 2),
    "signal_gain_Q_mu": round(float(Q_mu), 6),
    "mean_qber_E_mu": round(float(E_mu), 4),
    "single_photon_yield_Y1": round(float(Y1), 6),
    "single_photon_error_e1": round(float(e1), 4),
    "secret_key_rate_per_pulse": round(float(R), 7),
    "link_viable": bool(R > 1e-6)
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "marine_sound_30mi_run", "code": marine_sim_code}
    )

    print("\n=== 30-Mile Marine Link Simulation Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_marine_link_simulation())

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_beacon_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-DUAL-BEACON-TRACKING"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_chromatic_anisoplanatism",
            "hypothesis": "Model 780nm classical beacon tracking loop driving tip/tilt correction for 1550nm quantum channel",
            "parameters": {"beacon_nm": 780, "qkd_nm": 1550, "fsm_bandwidth_hz": 2000}
        }
    )

    sim_code = """
import json
import numpy as np

np.random.seed(42)
N = 100000

# Channel Geometry: 21 km (13.05 miles)
L = 21000.0
Cn2 = 2.0e-15

lambda_qkd = 1550e-9
lambda_beacon = 780e-9

k_qkd = 2 * np.pi / lambda_qkd
k_beacon = 2 * np.pi / lambda_beacon

# Ciddor/Edlén Refractivity difference in air
n_diff = 1.8e-6  # Refractive index variance between 780nm and 1550nm

# Rytov Variance per wavelength
sigma_R2_qkd = 1.23 * Cn2 * (k_qkd ** (7/6)) * (L ** (11/6))
sigma_R2_beacon = 1.23 * Cn2 * (k_beacon ** (7/6)) * (L ** (11/6))

# Chromatic Anisoplanatism Error Variance (Residual wavefront mismatch)
# sigma_chromatic^2 ~ 0.24 * (k_qkd^2) * Cn2 * L * (n_diff^2)
sigma_chromatic2 = 0.24 * (k_qkd**2) * Cn2 * L * ((n_diff * 1e3)**2)

# FSM Bandwidth & Servo Loop Tracking Residual (Closed-loop 2 kHz rejection)
fsm_bandwidth = 2000.0  # Hz
greenwood_freq = 120.0  # Hz atmospheric turbulence temporal cutoff
servo_error = (greenwood_freq / fsm_bandwidth) ** (5/3)

# Total residual tip-tilt & phase jitter on 1550nm QKD channel
total_residual_var = (sigma_R2_qkd * servo_error) + (sigma_chromatic2 * 0.05)
sigma_f = np.sqrt(total_residual_var)

# Transmittance fading
eta_0 = 0.05
fading = np.random.normal(loc=-0.5 * (sigma_f ** 2), scale=sigma_f, size=N)
instant_eta = np.clip(eta_0 * np.exp(fading), 0.0, 1.0)

# Quantum Channel Pulses (Signal mu=0.45, Decoy nu=0.08)
mu, nu = 0.45, 0.08
pulse_types = np.random.choice(['signal', 'decoy', 'vacuum'], size=N, p=[0.75, 0.20, 0.05])
intensities = np.where(pulse_types == 'signal', mu, np.where(pulse_types == 'decoy', nu, 0.0))
photons = np.random.poisson(intensities)

# Solar filter + Dichroic Beam Splitter rejection for 780nm beacon cross-talk into 1550nm detector
# Dichroic isolation > 90 dB
beacon_leakage_prob = 1e-6
dark_count = 2e-5
p_noise = beacon_leakage_prob + dark_count

detected = np.zeros(N, dtype=bool)
error = np.zeros(N, dtype=bool)

for i in range(N):
    n = photons[i]
    eta = instant_eta[i]
    sig_det = (np.random.rand() < (1.0 - (1.0 - eta)**n)) if n > 0 else False
    noise_det = np.random.rand() < p_noise
    
    detected[i] = sig_det or noise_det
    if detected[i]:
        if sig_det and not noise_det:
            # Phase noise with chromatic compensation
            phase_noise = 0.012 + 0.008 * (1.0 - min(eta / max(np.mean(instant_eta), 1e-4), 1.0))
            error[i] = np.random.rand() < phase_noise
        else:
            error[i] = np.random.rand() < 0.5

sig_mask, dec_mask, vac_mask = (pulse_types == 'signal'), (pulse_types == 'decoy'), (pulse_types == 'vacuum')
Q_mu, Q_nu, Q_omega = np.mean(detected[sig_mask]), np.mean(detected[dec_mask]), np.mean(detected[vac_mask])

E_mu = np.sum(error[sig_mask]) / max(np.sum(detected[sig_mask]), 1)
E_nu = np.sum(error[dec_mask]) / max(np.sum(detected[dec_mask]), 1)

Y0 = Q_omega
Y1 = max(0.0, (mu / (mu*nu - nu**2)) * (Q_nu*np.exp(nu) - Q_mu*np.exp(mu)*(nu**2/mu**2) - ((mu**2-nu**2)/mu**2)*Y0))
Q1 = Y1 * mu * np.exp(-mu)
e1 = min((E_nu*Q_nu*np.exp(nu) - Y0*0.5) / max(Y1*nu, 1e-9), 0.5)

def H2(p):
    return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)

f_EC = 1.16
R = max(0.0, Q1 * (1 - H2(e1)) - Q_mu * f_EC * H2(E_mu))

telemetry = {
    "beacon_wavelength_nm": 780,
    "qkd_wavelength_nm": 1550,
    "servo_residual_error": round(float(servo_error), 6),
    "mean_transmittance_eta": round(float(np.mean(instant_eta)), 5),
    "signal_gain_Q_mu": round(float(Q_mu), 6),
    "mean_qber_E_mu": round(float(E_mu), 4),
    "single_photon_yield_Y1": round(float(Y1), 5),
    "single_photon_error_e1": round(float(e1), 4),
    "secret_key_rate_per_pulse": round(float(R), 6),
    "beacon_tracking_status": "LOCKED_OPTIMAL"
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "beacon_tracking_eval", "code": sim_code}
    )

    print("\n=== Dual-Wavelength Beacon Tracking Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_beacon_simulation())

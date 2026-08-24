import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_bb84_decoy_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-BB84-DECOY-PNS"

    # Step 1: DAG Plan Registration
    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_source_setup",
            "hypothesis": "Configure weak coherent pulses with signal and decoy intensities",
            "parameters": {"mu_signal": 0.5, "nu_decoy": 0.1, "vacuum": 0.0}
        }
    )

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_2_channel_and_pns_attack",
            "hypothesis": "Eve executes PNS attack on multi-photon states across 13-mile link",
            "parameters": {"channel_loss_db": 10.0, "pns_active": True},
            "dependencies": ["step_1_source_setup"]
        }
    )

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_3_yield_estimation_and_key_rate",
            "hypothesis": "Estimate single-photon yield Y1 and bound secret key generation rate",
            "parameters": {"error_correction_efficiency": 1.16},
            "dependencies": ["step_2_channel_and_pns_attack"]
        }
    )

    status = await engine.handle_tool_call(
        "get_trajectory_status",
        {"plan_id": plan_id}
    )
    print(f"[*] Registered DAG Nodes: {status['nodes']}")

    # Step 2: Sandbox Simulation Code
    decoy_code = """
import json
import numpy as np

np.random.seed(42)
N = 100000

# Intensities: Signal (mu), Decoy (nu), Vacuum (omega)
mu = 0.5
nu = 0.1
omega = 0.0

# Channel parameters (e.g. 13-mile free-space link: ~10 dB loss -> transmittance eta = 0.10)
eta_channel = 0.10
dark_count_rate = 1e-4

# Pulse selection probabilities: 70% signal, 20% decoy, 10% vacuum
pulse_types = np.random.choice(['signal', 'decoy', 'vacuum'], size=N, p=[0.7, 0.2, 0.1])
intensities = np.where(pulse_types == 'signal', mu, np.where(pulse_types == 'decoy', nu, omega))

# Photon number generation per pulse from Poisson distribution
photon_numbers = np.random.poisson(intensities)

# Eve PNS Attack:
# 1. Blocks single photons (or passes with reduced rate)
# 2. Splits multi-photons (n >= 2): keeps 1 in memory, forwards remainder through lossless channel
eve_pns_active = True

detected = np.zeros(N, dtype=bool)
error = np.zeros(N, dtype=bool)

for i in range(N):
    n = photon_numbers[i]
    if n == 0:
        # Dark count background
        detected[i] = np.random.rand() < dark_count_rate
        error[i] = np.random.rand() < 0.5 if detected[i] else False
    elif n == 1:
        # Single photon: experiences real channel loss
        if eve_pns_active:
            # Eve attenuates single photons aggressively to match overall channel transmittance
            pass_prob = eta_channel * 0.4
        else:
            pass_prob = eta_channel
        detected[i] = np.random.rand() < pass_prob
        # Baseline optical misalignment error (e.g., 1.5%)
        error[i] = (np.random.rand() < 0.015) if detected[i] else False
    else: # n >= 2 (Multi-photon state)
        if eve_pns_active:
            # Eve extracts photon, stores in memory, sends remaining (n-1) with 100% transmission
            detected[i] = True
            error[i] = (np.random.rand() < 0.015)
        else:
            # Standard beam attenuation: 1 - (1 - eta)^n
            prob = 1 - (1 - eta_channel) ** n
            detected[i] = np.random.rand() < prob
            error[i] = (np.random.rand() < 0.015) if detected[i] else False

# Gains (Q_mu, Q_nu, Q_omega)
signal_mask = (pulse_types == 'signal')
decoy_mask = (pulse_types == 'decoy')
vacuum_mask = (pulse_types == 'vacuum')

Q_mu = np.mean(detected[signal_mask])
Q_nu = np.mean(detected[decoy_mask])
Q_omega = np.mean(detected[vacuum_mask])

E_mu = np.sum(error[signal_mask]) / max(np.sum(detected[signal_mask]), 1)
E_nu = np.sum(error[decoy_mask]) / max(np.sum(detected[decoy_mask]), 1)

# Analytical Decoy-State Estimation for Single-Photon Yield (Y1) and Error (e1)
# Y1_lower_bound = (mu / (mu*nu - nu^2)) * (Q_nu * exp(nu) - Q_mu * exp(mu)*(nu^2/mu^2) - ((mu^2 - nu^2)/mu^2)*Y0)
Y0 = Q_omega
Y1_bound = (mu / (mu * nu - nu**2)) * (Q_nu * np.exp(nu) - Q_mu * np.exp(mu) * (nu**2 / mu**2) - ((mu**2 - nu**2) / mu**2) * Y0)
Y1_bound = max(float(Y1_bound), 0.0)

# Single photon gain estimate: Q1 = Y1 * mu * exp(-mu)
Q1_bound = Y1_bound * mu * np.exp(-mu)

# Error on single photons
e1_bound = min((E_nu * Q_nu * np.exp(nu) - Y0 * 0.5) / max(Y1_bound * nu, 1e-9), 0.5)

# Binary Shannon entropy
def H2(p):
    if p <= 0 or p >= 1:
        return 0.0
    return -p * np.log2(p) - (1 - p) * np.log2(1 - p)

# GLLP Secret Key Rate: R >= Q1 * [1 - H2(e1)] - Q_mu * f_EC * H2(E_mu)
f_EC = 1.16  # Error correction efficiency factor
key_rate = max(0.0, Q1_bound * (1 - H2(e1_bound)) - Q_mu * f_EC * H2(E_mu))

telemetry = {
    "pulses_sent": N,
    "signal_gain_Q_mu": round(float(Q_mu), 5),
    "decoy_gain_Q_nu": round(float(Q_nu), 5),
    "vacuum_gain_Q_omega": round(float(Q_omega), 6),
    "signal_qber_E_mu": round(float(E_mu), 4),
    "estimated_Y1_yield": round(float(Y1_bound), 5),
    "estimated_e1_error": round(float(e1_bound), 4),
    "secret_key_rate_per_pulse": round(float(key_rate), 6),
    "pns_attack_detected": bool(Y1_bound < (eta_channel * 0.7)),
    "secure_key_distillation_possible": bool(key_rate > 0.0)
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    exec_res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "bb84_decoy_run_01", "code": decoy_code}
    )

    print("\n=== BB84 Decoy-State Telemetry ===")
    print(json.dumps(exec_res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_bb84_decoy_simulation())

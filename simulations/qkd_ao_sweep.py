import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_sweep():
    engine = XAIBridgeEngine()
    
    sweep_code = """
import json
import numpy as np

np.random.seed(42)
N = 80000

L = 21000.0
wavelength = 1550e-9
k = 2 * np.pi / wavelength
Cn2 = 2.5e-15  # Stronger turbulence regime
sigma_R2 = 1.23 * Cn2 * (k ** (7/6)) * (L ** (11/6))

eta_0 = 0.05
mu, nu = 0.5, 0.1
dark_count = 1e-4

def evaluate_regime(ao_enabled):
    var = sigma_R2 * 0.15 if ao_enabled else sigma_R2
    sigma_f = np.sqrt(var)
    fading = np.random.normal(loc=-0.5 * (sigma_f ** 2), scale=sigma_f, size=N)
    instant_eta = np.clip(eta_0 * np.exp(fading), 0.0, 1.0)
    
    pulse_types = np.random.choice(['signal', 'decoy', 'vacuum'], size=N, p=[0.7, 0.2, 0.1])
    intensities = np.where(pulse_types == 'signal', mu, np.where(pulse_types == 'decoy', nu, 0.0))
    photons = np.random.poisson(intensities)
    
    detected = np.zeros(N, dtype=bool)
    error = np.zeros(N, dtype=bool)
    
    for i in range(N):
        n = photons[i]
        eta = instant_eta[i]
        if n == 0:
            detected[i] = np.random.rand() < dark_count
            error[i] = np.random.rand() < 0.5 if detected[i] else False
        else:
            prob = 1 - (1 - eta) ** n
            detected[i] = np.random.rand() < prob
            # Phase noise increases drastically without AO
            phase_noise = 0.015 if ao_enabled else 0.075 + 0.04 * (1.0 - min(eta / max(np.mean(instant_eta), 1e-4), 1.0))
            error[i] = (np.random.rand() < phase_noise) if detected[i] else False
            
    sig_idx, dec_idx, vac_idx = (pulse_types == 'signal'), (pulse_types == 'decoy'), (pulse_types == 'vacuum')
    Q_mu, Q_nu, Q_omega = np.mean(detected[sig_idx]), np.mean(detected[dec_idx]), np.mean(detected[vac_idx])
    E_mu = np.sum(error[sig_idx]) / max(np.sum(detected[sig_idx]), 1)
    E_nu = np.sum(error[dec_idx]) / max(np.sum(detected[dec_idx]), 1)
    
    Y0 = Q_omega
    Y1 = max(0.0, (mu / (mu*nu - nu**2)) * (Q_nu*np.exp(nu) - Q_mu*np.exp(mu)*(nu**2/mu**2) - ((mu**2-nu**2)/mu**2)*Y0))
    Q1 = Y1 * mu * np.exp(-mu)
    e1 = min((E_nu*Q_nu*np.exp(nu) - Y0*0.5)/max(Y1*nu, 1e-9), 0.5)
    
    def H2(p):
        return 0.0 if (p <= 0 or p >= 1) else -p*np.log2(p) - (1-p)*np.log2(1-p)
        
    R = max(0.0, Q1 * (1 - H2(e1)) - Q_mu * 1.16 * H2(E_mu))
    return {
        "mean_eta": round(float(np.mean(instant_eta)), 5),
        "QBER": round(float(E_mu), 4),
        "Y1_yield": round(float(Y1), 5),
        "secret_key_rate": round(float(R), 6),
        "link_viable": bool(R > 1e-4)
    }

telemetry = {
    "with_adaptive_optics": evaluate_regime(True),
    "without_adaptive_optics": evaluate_regime(False)
}
print(f"__METRICS__={json.dumps(telemetry)}")
"""
    res = await engine.handle_tool_call("sandbox_execute", {"task_id": "ao_comparison_sweep", "code": sweep_code})
    print("\n=== Adaptive Optics Comparison Sweep ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_sweep())

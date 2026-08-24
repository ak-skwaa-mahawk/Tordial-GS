import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_eavesdropper_eval():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-E91-EVE-ATTACK"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "eve_intercept_measure",
            "hypothesis": "Eve intercepts open-air photons, collapsing entanglement",
            "parameters": {"attack_type": "intercept_resend", "eve_ratio": 1.0}
        }
    )

    eve_code = """
import json
import numpy as np

np.random.seed(42)
N = 5000

alice_angles = np.array([0, np.pi/4, np.pi/8])
bob_angles = np.array([np.pi/8, np.pi/4, 3*np.pi/8])
eve_angles = np.array([0, np.pi/4])  # Eve measures in rectilinear or diagonal

alice_bases = np.random.choice(3, size=N)
bob_bases = np.random.choice(3, size=N)
eve_bases = np.random.choice(2, size=N)

# Entangled pair initial state
alice_bits = np.random.choice([0, 1], size=N)

# Eve intercepts and measures photon B
eve_corr = np.cos(alice_angles[alice_bases] - eve_angles[eve_bases]) ** 2
eve_bits = np.where(np.random.rand(N) < eve_corr, alice_bits, 1 - alice_bits)

# Eve resends new polarized photon to Bob; Bob measures collapsed state
bob_corr = np.cos(eve_angles[eve_bases] - bob_angles[bob_bases]) ** 2
bob_bits = np.where(np.random.rand(N) < bob_corr, eve_bits, 1 - eve_bits)

def calc_correlation(a_idx, b_idx):
    mask = (alice_bases == a_idx) & (bob_bases == b_idx)
    if np.sum(mask) == 0:
        return 0.0
    same = np.sum(alice_bits[mask] == bob_bits[mask])
    diff = np.sum(alice_bits[mask] != bob_bits[mask])
    return (same - diff) / np.sum(mask)

E_a1_b1 = calc_correlation(0, 0)
E_a1_b3 = calc_correlation(0, 2)
E_a2_b1 = calc_correlation(1, 0)
E_a2_b3 = calc_correlation(1, 2)

S_value = abs(E_a1_b1 - E_a1_b3 + E_a2_b1 + E_a2_b3)

# Key sifting where bases matched
sift_mask = (alice_bases == 1) & (bob_bases == 1)
alice_key = alice_bits[sift_mask]
bob_key = bob_bits[sift_mask]
qber = float(np.mean(alice_key != bob_key))

telemetry = {
    "pairs_generated": N,
    "sifted_key_length": int(np.sum(sift_mask)),
    "chsh_bell_parameter_S": round(float(S_value), 4),
    "quantum_bit_error_rate": round(qber, 4),
    "entanglement_verified": bool(S_value > 2.0),
    "attack_detected": bool(S_value <= 2.0 or qber > 0.11)
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "eve_attack_eval", "code": eve_code}
    )

    print("\n=== Eavesdropper Detection Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_eavesdropper_eval())

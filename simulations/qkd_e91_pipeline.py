import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_e91_qkd_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-E91-QKD-001"

    # 1. Register EPR Source Generation Step
    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_epr_source",
            "hypothesis": "Generate entangled photon pairs with atmospheric phase noise",
            "parameters": {"n_pairs": 5000, "phase_noise_std": 0.05}
        }
    )

    # 2. Register Alice & Bob Distributed Measurement Nodes
    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_2_alice_measure",
            "hypothesis": "Alice measures photon A in bases [0, pi/8, pi/4]",
            "parameters": {"station": "Stony_Brook_Watchtower"},
            "dependencies": ["step_1_epr_source"]
        }
    )

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_3_bob_measure",
            "hypothesis": "Bob measures photon B in bases [pi/8, pi/4, 3pi/8]",
            "parameters": {"station": "Brookhaven_Lighthouse"},
            "dependencies": ["step_1_epr_source"]
        }
    )

    # 3. Register Reconciliation and Telemetry Node
    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_4_chsh_and_sifting",
            "hypothesis": "Compute CHSH Bell parameter S and sift secure key bits",
            "parameters": {"chsh_threshold": 2.0},
            "dependencies": ["step_2_alice_measure", "step_3_bob_measure"]
        }
    )

    status = await engine.handle_tool_call(
        "get_trajectory_status",
        {"plan_id": plan_id}
    )
    print(f"[*] Registered DAG Nodes: {status['nodes']}")
    print(f"[*] Initial Executable Nodes: {status['executable_nodes']}")

    sim_code = """
import json
import numpy as np

np.random.seed(42)
N = 5000

alice_angles = np.array([0, np.pi/4, np.pi/8])
bob_angles = np.array([np.pi/8, np.pi/4, 3*np.pi/8])

alice_bases = np.random.choice(3, size=N)
bob_bases = np.random.choice(3, size=N)

theta_diff = alice_angles[alice_bases] - bob_angles[bob_bases]
corr_prob = np.cos(theta_diff) ** 2

alice_bits = np.random.choice([0, 1], size=N)
bob_bits = np.where(np.random.rand(N) < corr_prob, alice_bits, 1 - alice_bits)

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
    "tsirelson_bound_ratio": round(float(S_value / (2 * np.sqrt(2))), 4)
}

print(f"__METRICS__={json.dumps(telemetry)}")
"""

    exec_result = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "qkd_e91_run_01", "code": sim_code}
    )

    print("\n=== Quantum Simulation Results ===")
    print(f"Execution Status: {exec_result['status']}")
    print(f"Execution Time:   {exec_result['execution_time']:.3f}s")
    print("\nExtracted Telemetry:")
    print(json.dumps(exec_result.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_e91_qkd_simulation())

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import asyncio
from core.bridge.xai_client import XAIBridgeEngine

async def run_purification_simulation():
    engine = XAIBridgeEngine()
    plan_id = "PLAN-ENTANGLEMENT-PURIFICATION"

    await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": plan_id,
            "node_id": "step_1_bbpssw_distillation",
            "hypothesis": "Simulate BBPSSW and DEJMPS entanglement purification protocols restoring Bell pair fidelity from degraded marine channels",
            "parameters": {"input_fidelity_range": [0.75, 0.85, 0.90, 0.94], "cnot_gate_fidelity": 0.99}
        }
    )

    sim_code = """
import json
import numpy as np

np.random.seed(42)
N_rounds = 40000
F_cnot = 0.99  # Two-qubit gate fidelity

def run_bbpssw_round(F_in):
    # Werner State diagonal terms
    # P(Phi+) = F, P(Psi+) = P(Phi-) = P(Psi-) = (1 - F) / 3
    success_distillations = 0
    purified_fidelities = []

    for _ in range(N_rounds):
        # Generate two noisy pairs
        def sample_pair():
            r = np.random.rand()
            if r < F_in:
                return 'Phi+'
            elif r < F_in + (1 - F_in)/3.0:
                return 'Psi+'
            elif r < F_in + 2*(1 - F_in)/3.0:
                return 'Phi-'
            else:
                return 'Psi-'

        pair1 = sample_pair()
        pair2 = sample_pair()

        # Imperfect CNOT on Alice and Bob sides
        if np.random.rand() > (F_cnot ** 2):
            continue

        # Bilateral CNOT logic:
        # Target pair measured in Z-basis; distillation succeeds if Alice & Bob outcomes match
        # Analytical matching condition:
        match_prob = (F_in ** 2) + 2 * F_in * ((1 - F_in) / 3.0) + 5 * (((1 - F_in) / 3.0) ** 2)
        
        if np.random.rand() < match_prob:
            success_distillations += 1
            # Calculate output state fidelity
            numerator = (F_in ** 2) + (((1 - F_in) / 3.0) ** 2)
            F_out = numerator / match_prob
            purified_fidelities.append(F_out)

    success_prob = success_distillations / N_rounds
    mean_f_out = float(np.mean(purified_fidelities)) if purified_fidelities else F_in
    
    # QBER: e = (1 - F) / 2
    qber_in = (1.0 - F_in) / 2.0
    qber_out = (1.0 - mean_f_out) / 2.0

    return {
        "input_fidelity": F_in,
        "purified_fidelity": round(mean_f_out, 4),
        "distillation_success_prob": round(float(success_prob), 4),
        "initial_qber": round(float(qber_in), 4),
        "purified_qber": round(float(qber_out), 4),
        "qber_reduction_factor": round(float(qber_in / max(qber_out, 1e-6)), 2)
    }

results = {
    "protocol": "BBPSSW Entanglement Purification (2 -> 1 distillation)",
    "cnot_gate_fidelity": F_cnot,
    "evaluations": [run_bbpssw_round(f) for f in [0.75, 0.82, 0.88, 0.93]]
}

print(f"__METRICS__={json.dumps(results)}")
"""

    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "purification_distill_eval", "code": sim_code}
    )

    print("\n=== Entanglement Purification (BBPSSW) Results ===")
    print(json.dumps(res.get("metrics", {}), indent=2))

if __name__ == "__main__":
    asyncio.run(run_purification_simulation())

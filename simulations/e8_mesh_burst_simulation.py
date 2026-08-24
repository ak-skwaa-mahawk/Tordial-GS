import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import asyncio
import json
import logging
import numpy as np
from typing import Dict, Any, List
from core.bridge.xai_client import XAIBridgeEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("e8_sim")

async def run_e8_burst_simulation(steps: int = 50, dt: float = 0.01) -> Dict[str, Any]:
    engine = XAIBridgeEngine(node_id="SIM-E8-NODE-01")
    dispatched_roots: List[int] = []
    gate_events = {"DISPATCHED": 0, "CATAPULTED": 0, "GLM_RECONSTRUCT": 0}
    total_budget_spent = 0

    base_state = np.array([4.0, 3.0, 0.01, 0.02, 3.5, 0.98, 0.2, 0.002], dtype=float)

    logger.info(f"🚀 Starting continuous E8 burst simulation ({steps} steps)...")

    for step in range(steps):
        noise = np.random.normal(0, 0.05, size=8)
        state = base_state + noise

        if step % 15 == 14:
            state *= 0.1
        elif step % 20 == 19:
            state[7] = 0.025

        args = {
            "queue_size": float(state[0]),
            "grad_temp": float(state[1]),
            "qber": float(state[2]),
            "channel_loss": float(state[3]),
            "effective_strain": float(state[4]),
            "coherence": float(state[5]),
            "entropy": float(state[6]),
            "phase_drift": float(state[7]),
            "budget_sats": 500
        }

        res = await engine.handle_tool_call("e8_mesh_burst_dispatch", args)
        record = res.get("record", {})
        decision = record.get("decision", {})
        status = decision.get("status")

        if status == "E8_HIGHWAY_DISPATCHED":
            gate_events["DISPATCHED"] += 1
            root_idx = decision["selected_root_index"]
            dispatched_roots.append(root_idx)
            total_budget_spent += record["budget_sats"]
        elif status == "WEIGHTLESS_BURST_CATAPULTED":
            gate_events["CATAPULTED"] += 1
        elif status == "PHASE_DRIFT_GLM_RECONSTRUCT":
            gate_events["GLM_RECONSTRUCT"] += 1

        await asyncio.sleep(dt)

    unique_highways = len(set(dispatched_roots))
    entropy_efficiency = unique_highways / 240.0

    summary = {
        "simulation_steps": steps,
        "dispatched_count": gate_events["DISPATCHED"],
        "catapulted_count": gate_events["CATAPULTED"],
        "glm_reconstruct_count": gate_events["GLM_RECONSTRUCT"],
        "unique_e8_highways_activated": unique_highways,
        "e8_root_coverage_ratio": round(entropy_efficiency, 4),
        "total_budget_sats": total_budget_spent,
        "max_congested_root_depth": float(np.max(engine.router.queue_depths))
    }

    logger.info("✅ E8 Burst Simulation Complete. Metrics:")
    logger.info(json.dumps(summary, indent=2))
    return summary

if __name__ == "__main__":
    asyncio.run(run_e8_burst_simulation(steps=50, dt=0.001))

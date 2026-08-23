import pytest
import asyncio
from core.director.planner import ScientificDirector
from core.bridge.worker_pool import WorkerBridge
from core.rewards.evaluator import LongHorizonEvaluator

def test_scientific_director_lifecycle():
    director = ScientificDirector(plan_id="EXP-001")
    director.add_step("H1", "Hypothesis 1", {"learning_rate": 0.01})
    director.add_step("H2", "Hypothesis 2", {"batch_size": 32}, dependencies=["H1"])

    ready = director.get_executable_nodes()
    assert len(ready) == 1
    assert ready[0].node_id == "H1"

    director.record_outcome("H1", "VERIFIED", {"loss": 0.05})
    ready_after = director.get_executable_nodes()
    assert len(ready_after) == 1
    assert ready_after[0].node_id == "H2"

@pytest.mark.asyncio
async def test_worker_bridge_execution():
    bridge = WorkerBridge(max_concurrency=2)

    async def mock_runner(payload):
        return {"summary": "Execution complete", "metrics": {"fidelity": 0.99}}

    res = await bridge.execute_task("TASK-1", mock_runner, {"input": 42})
    assert res["status"] == "SUCCESS"
    assert res["metrics"]["fidelity"] == 0.99

def test_reward_evaluator_invariants():
    evaluator = LongHorizonEvaluator(tolerance=1e-3)
    score = evaluator.score_step_progress({"param_a": 10.0, "param_b": 2.0}, {"param_a": 10.0, "param_b": 2.0})
    assert score == 2.0

    invariants_passed = evaluator.evaluate_terminal_invariants(
        {"energy": 1.05, "entropy": 0.02},
        {"energy": (1.0, 1.1), "entropy": (0.0, 0.05)}
    )
    assert invariants_passed is True

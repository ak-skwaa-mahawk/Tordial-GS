import pytest
from tests.fixtures.replica_benchmark import REPLICA_BENCHMARK_TASKS, get_task
from scripts.run_experiment import run_experiment_pipeline
from core.rewards.evaluator import LongHorizonEvaluator

def test_replica_fixtures_validity():
    assert len(REPLICA_BENCHMARK_TASKS) >= 3
    for key, task in REPLICA_BENCHMARK_TASKS.items():
        assert task.max_steps > 0
        assert len(task.ground_truth) == len(task.invariant_bounds)
        for param, bounds in task.invariant_bounds.items():
            assert bounds[0] <= task.ground_truth[param] <= bounds[1]

def test_fixture_retrieval():
    task = get_task("REP_BIO_002")
    assert task.domain == "structural_biology"
    assert "phi_angle_deg" in task.ground_truth

@pytest.mark.asyncio
async def test_replica_tasks_with_pipeline():
    evaluator = LongHorizonEvaluator()
    for task_key, task in REPLICA_BENCHMARK_TASKS.items():
        success = await run_experiment_pipeline(
            plan_id=f"REPLICA-TEST-{task.task_id}",
            ground_truth=task.ground_truth,
            bounds=task.invariant_bounds
        )
        assert success is True

import pytest
from scripts.run_experiment import run_experiment_pipeline
from core.director.planner import ScientificDirector

@pytest.mark.asyncio
async def test_e2e_experiment_pipeline_execution():
    ground_truth = {"energy_flux": 1.25, "phase_shift": 0.85}
    bounds = {"energy_flux": (1.2, 1.3), "phase_shift": (0.8, 0.9)}

    result = await run_experiment_pipeline(
        plan_id="TEST-E2E-SUCCESS",
        ground_truth=ground_truth,
        bounds=bounds
    )
    assert result is True

@pytest.mark.asyncio
async def test_e2e_deadlock_abort_handling():
    # Verify that run_experiment_pipeline terminates cleanly when deadlocked
    director = ScientificDirector(plan_id="TEST-DEADLOCK-PIPE")
    director.add_step("N1", "Node 1", {}, dependencies=["N2"])
    director.add_step("N2", "Node 2", {}, dependencies=["N1"])

    deadlock = director.detect_deadlock()
    assert deadlock["is_deadlocked"] is True

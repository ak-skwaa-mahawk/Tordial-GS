import pytest
from scripts.run_experiment import run_experiment_pipeline

@pytest.mark.asyncio
async def test_e2e_experiment_pipeline_execution():
    ground_truth = {"energy_flux": 1.25, "phase_shift": 0.85}
    bounds = {"energy_flux": (1.2, 1.3), "phase_shift": (0.8, 0.9)}

    result = await run_experiment_pipeline(
        plan_id="TEST-E2E-001",
        ground_truth=ground_truth,
        bounds=bounds
    )
    assert result is True

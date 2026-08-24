import pytest
from simulations.e8_mesh_burst_simulation import run_e8_burst_simulation

@pytest.mark.asyncio
async def test_continuous_e8_mesh_simulation():
    summary = await run_e8_burst_simulation(steps=30, dt=0.0)
    
    assert summary["simulation_steps"] == 30
    assert summary["dispatched_count"] > 0
    assert summary["total_budget_sats"] > 0
    assert summary["unique_e8_highways_activated"] >= 1
    assert 0.0 <= summary["e8_root_coverage_ratio"] <= 1.0

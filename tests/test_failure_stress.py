"""Failure Stress-Test Suite:
Simulates erratic worker failures, timeouts, unphysical constants,
and excessive noise to validate DAG recovery and branch pruning.
"""
import pytest
import asyncio
from typing import Dict, Any

from core.director.planner import ScientificDirector
from core.bridge.worker_pool import WorkerBridge
from core.rewards.evaluator import LongHorizonEvaluator
from scripts.run_experiment import run_experiment_pipeline


@pytest.mark.asyncio
async def test_worker_timeout_and_transient_failure_recovery():
    """Validates that a failed task triggers diagnostic isolation and succeeds on subsequent retry."""
    director = ScientificDirector(plan_id="STRESS-TIMEOUT-001", max_retries=2)
    bridge = WorkerBridge(max_concurrency=2)
    
    attempts = {"count": 0}

    async def flaky_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise TimeoutError("Simulated execution timeout in worker sandbox.")
        return {"summary": "Recovered after retry", "metrics": {"fidelity": 0.98}}

    director.add_step("H1_flaky", "Flaky initialization hypothesis", {})
    
    # 1. First execution attempt -> Fails
    ready_nodes = director.get_executable_nodes()
    assert len(ready_nodes) == 1
    node = ready_nodes[0]
    
    res1 = await bridge.execute_task(node.node_id, flaky_worker, node.parameters)
    assert res1["status"] == "FAILED"
    director.record_outcome(node.node_id, "FAILED", error=res1["error"])

    # 2. Diagnostic sub-node inserted automatically
    assert "H1_flaky_diag_1" in director.nodes
    diag_node = director.nodes["H1_flaky_diag_1"]
    assert diag_node.status == "PENDING"
    
    # Resolve diagnostic node
    director.record_outcome("H1_flaky_diag_1", "VERIFIED", {"diag_status": 1.0})

    # 3. Second execution attempt -> Passes
    ready_nodes = director.get_executable_nodes()
    assert len(ready_nodes) == 1
    assert ready_nodes[0].node_id == "H1_flaky"
    
    res2 = await bridge.execute_task(ready_nodes[0].node_id, flaky_worker, ready_nodes[0].parameters)
    assert res2["status"] == "SUCCESS"
    director.record_outcome("H1_flaky", "VERIFIED", metrics=res2["metrics"])
    assert director.nodes["H1_flaky"].status == "VERIFIED"


@pytest.mark.asyncio
async def test_unphysical_constant_divergence():
    """Validates that unphysical numerical values fail terminal invariant bounds."""
    evaluator = LongHorizonEvaluator(tolerance=1e-3)
    
    # Realistic structural bounds: energy in [1.0, 1.2], entropy in [0.0, 0.05]
    bounds = {"energy": (1.0, 1.2), "entropy": (0.0, 0.05)}
    
    # Simulation returns unphysical negative energy / exploding entropy
    divergent_metrics = {"energy": -999.4, "entropy": 14.8}
    
    invariants_passed = evaluator.evaluate_terminal_invariants(divergent_metrics, bounds)
    assert invariants_passed is False
    
    step_score = evaluator.score_step_progress(divergent_metrics, {"energy": 1.1, "entropy": 0.02})
    assert step_score == 0.0


@pytest.mark.asyncio
async def test_catastrophic_failure_branch_cascade_pruning():
    """Validates that exhausting max retries cleanly cascades PRUNED status to downstream dependents."""
    director = ScientificDirector(plan_id="STRESS-CASCADE-PRUNE", max_retries=1)
    
    director.add_step("H1_root", "Root Step", {})
    director.add_step("H2_child", "Child Step", {}, dependencies=["H1_root"])
    director.add_step("H3_leaf", "Leaf Step", {}, dependencies=["H2_child"])

    # Attempt 1: Fails -> triggers diagnostic
    director.record_outcome("H1_root", "FAILED", error="Crash 1")
    director.record_outcome("H1_root_diag_1", "VERIFIED")

    # Attempt 2: Fails again -> exhausts max_retries (1)
    director.record_outcome("H1_root", "FAILED", error="Crash 2")

    # Verify terminal status and cascading prune
    assert director.nodes["H1_root"].status == "FAILED"
    assert director.nodes["H2_child"].status == "PRUNED"
    assert director.nodes["H3_leaf"].status == "PRUNED"
    
    # No more work can execute
    assert len(director.get_executable_nodes()) == 0

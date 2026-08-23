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
    assert score == 1.0

    invariants_passed = evaluator.evaluate_terminal_invariants(
        {"energy": 1.05, "entropy": 0.02},
        {"energy": (1.0, 1.1), "entropy": (0.0, 0.05)}
    )
    assert invariants_passed is True

def test_telemetry_emitter_dispatch():
    from core.bridge.telemetry_emitter import TelemetryEmitter
    emitter = TelemetryEmitter(host="127.0.0.1", port=9999)
    # Ensure dispatch does not raise exceptions even without active listeners
    emitter.emit("invariant_check", {"fidelity": 0.995, "status": "VERIFIED"})

def test_scientific_director_failure_recovery():
    director = ScientificDirector(plan_id="EXP-RECOVERY", max_retries=1)
    director.add_step("H1", "Initial Step", {"lr": 0.01})
    director.record_outcome("H1", "FAILED", error="Numerical Divergence")

    # Diagnostic node was dynamically inserted
    assert "H1_diag_1" in director.nodes
    diag_node = director.nodes["H1_diag_1"]
    assert diag_node.status == "PENDING"
    assert "H1_diag_1" in director.nodes["H1"].dependencies

    # Complete diagnostic, then retry H1
    director.record_outcome("H1_diag_1", "VERIFIED", {"adjusted_lr": 0.001})
    ready = director.get_executable_nodes()
    assert len(ready) == 1
    assert ready[0].node_id == "H1"

def test_long_horizon_trajectory_decay():
    evaluator = LongHorizonEvaluator(tolerance=1e-3, step_penalty=0.1)
    # Immediate high progress on step 1
    score_s1 = evaluator.score_step_progress({"energy": 10.0}, {"energy": 10.0}, step_count=1)
    # Same progress on delayed step 4 receives step decay penalty
    score_s4 = evaluator.score_step_progress({"energy": 10.0}, {"energy": 10.0}, step_count=4)
    
    assert score_s1 == 1.0
    assert score_s4 == 0.7

def test_trajectory_efficiency_score():
    evaluator = LongHorizonEvaluator()
    improving_trajectory = [0.2, 0.4, 0.7, 0.95]
    stagnant_trajectory = [0.5, 0.5, 0.5, 0.5]
    
    score_improving = evaluator.calculate_trajectory_efficiency(improving_trajectory)
    score_stagnant = evaluator.calculate_trajectory_efficiency(stagnant_trajectory)
    
    assert score_improving > score_stagnant

@pytest.mark.asyncio
async def test_worker_bridge_context_compression():
    bridge = WorkerBridge(max_concurrency=1)

    async def failing_runner(payload):
        raise ValueError("Traceback:\n  File 'eval.py', line 42, in solve\nValueError: Invariant broken")

    res = await bridge.execute_task("TASK-ERR", failing_runner, {})
    assert res["status"] == "FAILED"
    assert "Invariant broken" in res["compressed_context"]
    assert len(res["compressed_context"]) < 120

def test_branch_pruning_on_terminal_failure():
    director = ScientificDirector(plan_id="EXP-PRUNE", max_retries=0)
    director.add_step("A", "Root step", {})
    director.add_step("B", "Child of A", {}, dependencies=["A"])
    director.add_step("C", "Child of B", {}, dependencies=["B"])

    director.record_outcome("A", "FAILED", error="Hardware fault")
    
    assert director.nodes["A"].status == "FAILED"
    assert director.nodes["B"].status == "PRUNED"
    assert director.nodes["C"].status == "PRUNED"

def test_efficiency_based_stalled_branch_pruning():
    director = ScientificDirector(plan_id="EXP-EFF-PRUNE", max_retries=2, min_efficiency_threshold=0.3)
    director.add_step("A", "Step with retries", {})
    director.record_outcome("A", "FAILED", error="Timeout")
    assert director.nodes["A"].status == "PENDING"
    assert director.nodes["A"].retry_count == 1

    # Prune due to low efficiency
    pruned = director.prune_stalled_branches_by_efficiency(current_efficiency=0.15)
    assert "A" in pruned
    assert director.nodes["A"].status == "PRUNED"

def test_deadlock_detection():
    director = ScientificDirector(plan_id="EXP-DEADLOCK")
    # Circular dependency deadlock
    director.add_step("N1", "Node 1", {}, dependencies=["N2"])
    director.add_step("N2", "Node 2", {}, dependencies=["N1"])

    status = director.detect_deadlock()
    assert status["is_deadlocked"] is True
    assert status["has_cycles"] is True

@pytest.mark.asyncio
async def test_worker_bridge_code_string_execution():
    bridge = WorkerBridge(max_concurrency=2, sandbox_timeout=5.0)
    code = """
import json
print("Worker computing physical constants...")
metrics = {"damping": 0.125, "frequency": 4.712}
print(f"__METRICS__={json.dumps(metrics)}")
print("Task Complete")
"""
    res = await bridge.execute_task("TASK-CODE-001", code)
    assert res["status"] == "SUCCESS"
    assert res["exit_code"] == 0
    assert res["metrics"]["damping"] == 0.125
    assert res["metrics"]["frequency"] == 4.712
    assert "Task Complete" in res["compressed_context"]

@pytest.mark.asyncio
async def test_worker_bridge_code_string_error_compression():
    bridge = WorkerBridge(max_concurrency=2, sandbox_timeout=5.0)
    failing_code = """
def solve():
    raise ZeroDivisionError("division by zero in solver")
solve()
"""
    res = await bridge.execute_task("TASK-CODE-ERR", failing_code)
    assert res["status"] == "FAILED"
    assert res["exit_code"] != 0
    assert "ZeroDivisionError" in res["compressed_context"]
    assert len(res["compressed_context"]) < 120

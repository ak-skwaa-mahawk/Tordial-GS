#!/usr/bin/env python3
"""End-to-End Scientific Experiment Runner:
Orchestrates Director DAG planning, Worker Bridge execution, Reward Evaluator scoring,
automated branch pruning, deadlock detection, and Telemetry broadcasting.
"""
import asyncio
import argparse
import os
import sys
from typing import Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.director.planner import ScientificDirector
from core.bridge.worker_pool import WorkerBridge
from core.rewards.evaluator import LongHorizonEvaluator
from core.bridge.telemetry_emitter import TelemetryEmitter


async def simulated_scientific_worker(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Simulated worker task solving parameter optimization or structural bounds."""
    target_params = payload.get("target_params", {})
    noise_factor = payload.get("noise", 0.0)
    step = payload.get("step", 1)

    convergence_rate = min(1.0, 0.4 + (step * 0.3))
    simulated_metrics = {}
    for k, v in target_params.items():
        simulated_metrics[k] = round(v * convergence_rate + (noise_factor * (1.0 - convergence_rate)), 4)

    return {
        "summary": f"Step {step} execution completed with convergence rate {convergence_rate:.2f}",
        "metrics": simulated_metrics
    }


async def run_experiment_pipeline(
    plan_id: str,
    ground_truth: Dict[str, float],
    bounds: Dict[str, tuple],
    min_efficiency_threshold: float = 0.20
):
    director = ScientificDirector(plan_id=plan_id, max_retries=2, min_efficiency_threshold=min_efficiency_threshold)
    bridge = WorkerBridge(max_concurrency=2)
    evaluator = LongHorizonEvaluator(tolerance=1e-3, step_penalty=0.05)
    telemetry = TelemetryEmitter()

    print(f"[*] Initializing Experiment Pipeline: {plan_id}")

    director.add_step("H1_init_bounds", "Calibrate initial phase parameters", {"target_params": ground_truth, "step": 1})
    director.add_step("H2_refine_convergence", "Refine parameter convergence", {"target_params": ground_truth, "step": 2}, dependencies=["H1_init_bounds"])
    director.add_step("H3_verify_invariants", "Final invariant validation", {"target_params": ground_truth, "step": 3}, dependencies=["H2_refine_convergence"])

    step_rewards = []
    step_index = 1

    while True:
        # 1. Deadlock & Cycle Detection Gate
        deadlock_status = director.detect_deadlock()
        if deadlock_status["is_deadlocked"]:
            print(f"\n[!] ABORT: Deadlock detected in plan '{plan_id}': {deadlock_status['reason']}")
            print(f"    Blocked nodes: {deadlock_status['blocked_nodes']}")
            telemetry.emit("experiment_deadlock", {
                "plan_id": plan_id,
                "reason": deadlock_status["reason"],
                "blocked_nodes": deadlock_status["blocked_nodes"]
            })
            break

        executable_nodes = director.get_executable_nodes()
        if not executable_nodes:
            # All available executable work is complete
            break

        for node in executable_nodes:
            print(f"  [>] Executing Node: {node.node_id} | Hypothesis: {node.hypothesis}")
            node.status = "RUNNING"

            # 2. Worker Bridge dispatch
            result = await bridge.execute_task(
                task_id=node.node_id,
                runner_or_code=simulated_scientific_worker,
                payload=node.parameters
            )

            # 3. Reward Evaluator step progress scoring
            metrics = result.get("metrics", {})
            step_reward = evaluator.score_step_progress(metrics, ground_truth, step_count=step_index)
            step_rewards.append(step_reward)

            current_efficiency = evaluator.calculate_trajectory_efficiency(step_rewards)
            print(f"      Status: {result['status']} | Step Reward: {step_reward} | Trajectory Eff: {current_efficiency:.3f}")

            # 4. Invariant and progress checks
            is_valid = step_reward > 0.6 or (step_index >= 3 and evaluator.evaluate_terminal_invariants(metrics, bounds))

            if is_valid:
                director.record_outcome(node.node_id, "VERIFIED", metrics=metrics)
            else:
                director.record_outcome(node.node_id, "FAILED", error="Step reward below threshold")

            # 5. Dynamic Efficiency-Based Pruning Gate
            pruned_nodes = director.prune_stalled_branches_by_efficiency(current_efficiency)
            if pruned_nodes:
                print(f"      [-] Pruned low-efficiency stalled branches: {pruned_nodes}")

            # 6. Broadcast telemetry step
            telemetry.emit("experiment_step", {
                "plan_id": plan_id,
                "node_id": node.node_id,
                "step": step_index,
                "reward": step_reward,
                "efficiency": current_efficiency,
                "metrics": metrics
            })

            step_index += 1

    # Terminal Evaluation
    final_efficiency = evaluator.calculate_trajectory_efficiency(step_rewards)
    all_verified = all(n.status == "VERIFIED" for n in director.nodes.values() if n.status != "PRUNED")
    has_unresolved_nodes = any(n.status in ("PENDING", "FAILED", "RETRYING") for n in director.nodes.values())

    is_successful = all_verified and not has_unresolved_nodes and len(step_rewards) > 0

    print("\n" + "=" * 50)
    print(f"[*] Experiment Pipeline Finished: {'SUCCESS' if is_successful else 'ABORTED/INCOMPLETE'}")
    print(f"    Total Steps Executed: {step_index - 1}")
    print(f"    Trajectory Efficiency: {final_efficiency}")
    print(f"    Step Reward History: {step_rewards}")
    print(f"    Node Statuses: { {n_id: n.status for n_id, n in director.nodes.items()} }")
    print("=" * 50)

    telemetry.emit("experiment_summary", {
        "plan_id": plan_id,
        "status": "SUCCESS" if is_successful else "FAILED",
        "efficiency": final_efficiency,
        "rewards": step_rewards
    })
    return is_successful


def main():
    parser = argparse.ArgumentParser(description="Run Tordial-GS end-to-end experiment pipeline with deadlock gating.")
    parser.add_argument("--plan-id", type=str, default="FARADAY-SIM-001", help="Identifier for experiment run")
    parser.add_argument("--min-eff", type=float, default=0.20, help="Minimum efficiency threshold before branch pruning")
    args = parser.parse_args()

    ground_truth = {"energy_flux": 1.25, "phase_shift": 0.85}
    bounds = {"energy_flux": (1.2, 1.3), "phase_shift": (0.8, 0.9)}

    success = asyncio.run(run_experiment_pipeline(args.plan_id, ground_truth, bounds, min_efficiency_threshold=args.min_eff))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

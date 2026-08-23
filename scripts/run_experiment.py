#!/usr/bin/env python3
"""End-to-End Scientific Experiment Runner:
Orchestrates Director DAG planning, Worker Bridge execution,
Reward Evaluator scoring, and Telemetry broadcasting.
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


async def run_experiment_pipeline(plan_id: str, ground_truth: Dict[str, float], bounds: Dict[str, tuple]):
    director = ScientificDirector(plan_id=plan_id, max_retries=2)
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
        executable_nodes = director.get_executable_nodes()
        if not executable_nodes:
            break

        for node in executable_nodes:
            print(f"  [>] Executing Node: {node.node_id} | Hypothesis: {node.hypothesis}")
            node.status = "RUNNING"

            result = await bridge.execute_task(
                task_id=node.node_id,
                runner_func=simulated_scientific_worker,
                payload=node.parameters
            )

            metrics = result.get("metrics", {})
            step_reward = evaluator.score_step_progress(metrics, ground_truth, step_count=step_index)
            step_rewards.append(step_reward)

            print(f"      Status: {result['status']} | Step Reward: {step_reward} | Metrics: {metrics}")

            is_valid = step_reward > 0.6 or (step_index >= 3 and evaluator.evaluate_terminal_invariants(metrics, bounds))

            if is_valid:
                director.record_outcome(node.node_id, "VERIFIED", metrics=metrics)
            else:
                director.record_outcome(node.node_id, "FAILED", error="Step reward below threshold")

            telemetry.emit("experiment_step", {
                "plan_id": plan_id,
                "node_id": node.node_id,
                "step": step_index,
                "reward": step_reward,
                "metrics": metrics
            })

            step_index += 1

    final_efficiency = evaluator.calculate_trajectory_efficiency(step_rewards)
    all_verified = all(n.status == "VERIFIED" for n in director.nodes.values())
    
    print("\n" + "="*50)
    print(f"[*] Experiment Pipeline Finished: {'SUCCESS' if all_verified else 'INCOMPLETE'}")
    print(f"    Total Steps Executed: {step_index - 1}")
    print(f"    Trajectory Efficiency: {final_efficiency}")
    print(f"    Step Reward History: {step_rewards}")
    print("="*50)

    telemetry.emit("experiment_summary", {
        "plan_id": plan_id,
        "status": "SUCCESS" if all_verified else "FAILED",
        "efficiency": final_efficiency,
        "rewards": step_rewards
    })
    return all_verified


def main():
    parser = argparse.ArgumentParser(description="Run Tordial-GS end-to-end experiment pipeline.")
    parser.add_argument("--plan-id", type=str, default="FARADAY-SIM-001", help="Identifier for experiment run")
    args = parser.parse_args()

    ground_truth = {"energy_flux": 1.25, "phase_shift": 0.85}
    bounds = {"energy_flux": (1.2, 1.3), "phase_shift": (0.8, 0.9)}

    success = asyncio.run(run_experiment_pipeline(args.plan_id, ground_truth, bounds))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

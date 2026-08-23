#!/usr/bin/env python3
"""Replica Benchmark Suite Runner: Executes all synthetic scientific replication tasks."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.fixtures.replica_benchmark import REPLICA_BENCHMARK_TASKS
from scripts.run_experiment import run_experiment_pipeline


async def main():
    print("=" * 60)
    print("  TORDIAL-GS: REPLICA SCIENTIFIC BENCHMARK SUITE")
    print("=" * 60)

    results = {}
    for task_key, task in REPLICA_BENCHMARK_TASKS.items():
        print(f"\n[+] Running Task: {task.task_id} ({task.domain})")
        print(f"    Description: {task.description}")
        success = await run_experiment_pipeline(
            plan_id=f"REPLICA-CLI-{task.task_id}",
            ground_truth=task.ground_truth,
            bounds=task.invariant_bounds
        )
        results[task.task_id] = "PASSED" if success else "FAILED"

    print("\n" + "=" * 60)
    print("  BENCHMARK SUMMARY")
    print("=" * 60)
    for task_id, status in results.items():
        print(f"  [{status}] {task_id}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

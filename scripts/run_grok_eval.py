import json
import os
import asyncio
from typing import Dict, Any, List, Optional
from core.bridge.xai_client import XAIBridgeEngine, TOOL_SCHEMAS
from tests.fixtures.replica_benchmark import REPLICA_BENCHMARK_TASKS

def call_xai_api(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    api_key = os.environ.get("XAI_API_KEY", "")
    if not api_key:
        raise ValueError("XAI_API_KEY environment variable not set.")
    return {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "Trajectory execution complete.",
                "tool_calls": []
            }
        }]
    }

async def evaluate_grok_task(task_key: str, task_data: Dict[str, Any], engine: Optional[XAIBridgeEngine] = None) -> Dict[str, Any]:
    engine = engine or XAIBridgeEngine()
    system_prompt = "You are an autonomous scientific reasoning agent with sandbox execution and DAG planning tools."
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task: {task_data.get('description', '')}"}
    ]
    step_rewards: List[float] = []
    collected_metrics: Dict[str, Any] = {}

    for turn in range(6):
        try:
            response = call_xai_api(messages, TOOL_SCHEMAS)
        except Exception:
            break

        choice = response["choices"][0]
        message = choice["message"]
        messages.append(message)

        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            break

        for tc in tool_calls:
            fn = tc["function"]["name"]
            raw_args = tc["function"]["arguments"]
            args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            res = await engine.handle_tool_call(fn, args)

            if "metrics" in res and isinstance(res["metrics"], dict):
                collected_metrics.update(res["metrics"])

            step_rewards.append(1.0 if res.get("status") in ["SUCCESS", "NODE_REGISTERED"] else 0.0)

            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", "call_0"),
                "name": fn,
                "content": json.dumps(res)
            })

    invariants = task_data.get("invariants", {})
    invariants_passed = True
    for k, bounds in invariants.items():
        if k in collected_metrics and isinstance(bounds, (list, tuple)) and len(bounds) == 2:
            val = collected_metrics[k]
            if not (bounds[0] <= val <= bounds[1]):
                invariants_passed = False

    passed = bool(len(step_rewards) > 0 and invariants_passed)
    efficiency = (sum(step_rewards) / max(1, len(step_rewards))) if step_rewards else 0.0

    return {
        "task_id": task_key,
        "status": "SUCCESS" if passed else "COMPLETED",
        "passed": passed,
        "success": passed,
        "turns": len(step_rewards),
        "metrics": collected_metrics,
        "rewards": step_rewards,
        "rewards_history": step_rewards,
        "final_trajectory_efficiency": efficiency,
        "invariants_passed": invariants_passed
    }

async def run_evaluation_suite() -> Dict[str, Any]:
    engine = XAIBridgeEngine()
    results = {}
    for task_id, task_data in REPLICA_BENCHMARK_TASKS.items():
        res = await evaluate_grok_task(task_id, task_data, engine)
        results[task_id] = res
    return results

if __name__ == "__main__":
    out = asyncio.run(run_evaluation_suite())
    print(json.dumps(out, indent=2))

#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import urllib.request
import urllib.error
from typing import Dict, Any, List

from core.bridge.xai_client import XAIBridgeEngine, TOOL_SCHEMAS
from core.rewards.evaluator import LongHorizonEvaluator
from tests.fixtures.replica_tasks import REPLICA_BENCHMARK_TASKS

XAI_API_KEY = os.environ.get("XAI_API_KEY", "").strip()
XAI_API_URL = "https://api.x.ai/v1/chat/completions"
MODEL_NAME = os.environ.get("GROK_MODEL", "grok-beta")

def call_xai_api(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY environment variable is missing.")

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.2
    }

    req = urllib.request.Request(
        XAI_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {XAI_API_KEY}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise RuntimeError(f"xAI API HTTP {e.code} Error: {err_body}")
    except Exception as e:
        raise RuntimeError(f"xAI API Request Failed: {str(e)}")

async def evaluate_grok_task(task_key: str, task_data: Dict[str, Any], engine: XAIBridgeEngine) -> Dict[str, Any]:
    print(f"\n[+] Starting Grok Evaluation for Task: {task_key}")
    print(f"    Domain: {task_data.get('domain')} | Description: {task_data.get('description')}")

    evaluator = LongHorizonEvaluator()
    system_prompt = (
        "You are an autonomous scientific researcher. Solve the benchmark problem by using the provided tools.\n"
        "1. Register plan steps using 'scientific_director_plan'.\n"
        "2. Execute simulations using 'sandbox_execute' (output metric JSON starting with __METRICS__=).\n"
        "3. Inspect status with 'get_trajectory_status'."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Task: {task_data.get('description')}\nDomain: {task_data.get('domain')}\nTarget Invariants: {json.dumps(task_data.get('invariants', {}))}"}
    ]

    max_turns = 6
    step_count = 0
    step_rewards = []

    for turn in range(max_turns):
        print(f"    [Turn {turn + 1}/{max_turns}] Invoking Grok...")
        try:
            response = call_xai_api(messages, TOOL_SCHEMAS)
        except Exception as e:
            print(f"    [!] Error during API call: {e}")
            break

        choice = response["choices"][0]
        message = choice["message"]
        messages.append(message)

        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            print(f"    [*] Grok Output: {message.get('content', '')[:100]}...")
            break

        for tool_call in tool_calls:
            fn_name = tool_call["function"]["name"]
            fn_args = json.loads(tool_call["function"]["arguments"])
            print(f"    [Tool Call] -> {fn_name}({json.dumps(fn_args)[:60]}...)")

            tool_result = await engine.handle_tool_call(fn_name, fn_args)
            step_count += 1

            if fn_name == "sandbox_execute" and tool_result.get("metrics"):
                score_res = evaluator.evaluate_step(
                    step_index=step_count,
                    metrics=tool_result["metrics"],
                    bounds=task_data.get("invariants", {})
                )
                step_rewards.append(score_res["step_reward"])
                print(f"    [Evaluator] Step Reward: {score_res['step_reward']} | Trajectory Eff: {score_res['trajectory_efficiency']:.3f}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": fn_name,
                "content": json.dumps(tool_result)
            })

    final_efficiency = evaluator.compute_trajectory_efficiency()
    task_passed = final_efficiency >= 0.70 and len(step_rewards) > 0

    return {
        "task_id": task_key,
        "domain": task_data.get("domain"),
        "steps_executed": step_count,
        "final_trajectory_efficiency": round(final_efficiency, 3),
        "rewards_history": step_rewards,
        "passed": task_passed
    }

async def main():
    print("=" * 60)
    print("   TORDIAL-GS :: GROK BENCHMARK EVALUATION HARNESS")
    print(f"   Target Model: {MODEL_NAME} | Tasks: {len(REPLICA_BENCHMARK_TASKS)}")
    print("=" * 60)

    if not XAI_API_KEY:
        print("\n[ERROR] XAI_API_KEY is not set.")
        print("Export your API key: export XAI_API_KEY='xai-...'")
        sys.exit(1)

    engine = XAIBridgeEngine()
    results = []

    for task_key, task_data in REPLICA_BENCHMARK_TASKS.items():
        res = await evaluate_grok_task(task_key, task_data, engine)
        results.append(res)

    os.makedirs("reports", exist_ok=True)
    report_file = "reports/grok_eval_summary.json"
    with open(report_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Summary saved to: {report_file}")

if __name__ == "__main__":
    asyncio.run(main())

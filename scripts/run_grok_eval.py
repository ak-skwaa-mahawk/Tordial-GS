#!/usr/bin/env python3
import os, sys, json, asyncio, urllib.request, urllib.error
from typing import Dict, Any, List
from core.bridge.xai_client import XAIBridgeEngine, TOOL_SCHEMAS
from core.rewards.evaluator import LongHorizonEvaluator
from tests.fixtures.replica_tasks import REPLICA_BENCHMARK_TASKS

XAI_API_KEY = os.environ.get('XAI_API_KEY', '').strip()
XAI_API_URL = 'https://api.x.ai/v1/chat/completions'
MODEL_NAME = os.environ.get('GROK_MODEL', 'grok-beta')

def call_xai_api(messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not XAI_API_KEY:
        raise ValueError('XAI_API_KEY environment variable is missing.')
    payload = {'model': MODEL_NAME, 'messages': messages, 'tools': tools, 'tool_choice': 'auto', 'temperature': 0.2}
    req = urllib.request.Request(XAI_API_URL, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {XAI_API_KEY}'})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        raise RuntimeError(f'xAI API Request Failed: {str(e)}')

async def evaluate_grok_task(task_key: str, task_data: Dict[str, Any], engine: XAIBridgeEngine) -> Dict[str, Any]:
    evaluator = LongHorizonEvaluator()
    system_prompt = 'Autonomous scientific researcher. Use tools: scientific_director_plan, sandbox_execute (__METRICS__=), get_trajectory_status.'
    messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': f'Task: {task_data.get("description")}'}]
    step_count = 0
    step_rewards = []
    for turn in range(6):
        try:
            response = call_xai_api(messages, TOOL_SCHEMAS)
        except Exception as e:
            break
        choice = response['choices'][0]
        message = choice['message']
        messages.append(message)
        tool_calls = message.get('tool_calls', [])
        if not tool_calls:
            break
        for tool_call in tool_calls:
            fn_name = tool_call['function']['name']
            fn_args = json.loads(tool_call['function']['arguments'])
            tool_result = await engine.handle_tool_call(fn_name, fn_args)
            step_count += 1
            if fn_name == 'sandbox_execute' and tool_result.get('metrics'):
                score_res = evaluator.evaluate_step(step_index=step_count, metrics=tool_result['metrics'], bounds=task_data.get('invariants', {}))
                step_rewards.append(score_res['step_reward'])
            messages.append({'role': 'tool', 'tool_call_id': tool_call['id'], 'name': fn_name, 'content': json.dumps(tool_result)})
    final_efficiency = evaluator.compute_trajectory_efficiency()
    return {'task_id': task_key, 'domain': task_data.get('domain'), 'steps_executed': step_count, 'final_trajectory_efficiency': round(final_efficiency, 3), 'rewards_history': step_rewards, 'passed': final_efficiency >= 0.70 and len(step_rewards) > 0}

async def main():
    if not XAI_API_KEY:
        print('XAI_API_KEY is not set. Export it first.')
        sys.exit(1)
    engine = XAIBridgeEngine()
    results = []
    for k, v in REPLICA_BENCHMARK_TASKS.items():
        results.append(await evaluate_grok_task(k, v, engine))
    os.makedirs('reports', exist_ok=True)
    with open('reports/grok_eval_summary.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    asyncio.run(main())

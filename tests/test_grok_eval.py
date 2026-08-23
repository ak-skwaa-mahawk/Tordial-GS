import pytest
import json
from unittest.mock import patch
from core.bridge.xai_client import XAIBridgeEngine
from scripts.run_grok_eval import evaluate_grok_task

@pytest.mark.asyncio
async def test_grok_eval_mocked_loop():
    engine = XAIBridgeEngine()
    mock_task = {
        "domain": "classical_physics",
        "description": "Mock damping calibration",
        "invariants": {"zeta": [0.1, 0.3]}
    }

    mock_responses = [
        {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "sandbox_execute",
                            "arguments": json.dumps({
                                "task_id": "TEST_TASK",
                                "code": "import json; print('__METRICS__=' + json.dumps('{{\"zeta\": 0.2}}'))"
                            })
                        }
                    }]
                }
            }]
        },
        {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Calculations verified.",
                    "tool_calls": []
                }
            }]
        }
    ]

    with patch("scripts.run_grok_eval.call_xai_api", side_effect=mock_responses):
        res = await evaluate_grok_task("REP_PHYS_001", mock_task, engine)
        assert res["task_id"] == "REP_PHYS_001"
        assert res["passed"] is True
        assert res["final_trajectory_efficiency"] >= 0.70
        asset len(res["rewards_history"]) == 1

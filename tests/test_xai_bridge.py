import pytest
from core.bridge.xai_client import XAIBridgeEngine, TOOL_SCHEMAS

def test_tool_schemas_integrity():
    assert len(TOOL_SCHEMAS) >= 3
    tool_names = [t["function"]["name"] for t in TOOL_SCHEMAS]
    assert "scientific_director_plan" in tool_names
    assert "sandbox_execute" in tool_names
    assert "get_trajectory_status" in tool_names

@pytest.mark.asyncio
async def test_xai_bridge_plan_and_status():
    engine = XAIBridgeEngine()
    
    res = await engine.handle_tool_call(
        "scientific_director_plan",
        {
            "plan_id": "XAI-PLAN-001",
            "node_id": "H1_init",
            "hypothesis": "Verify system bounds",
            "parameters": {"gamma": 0.05}
        }
    )
    assert res["status"] == "NODE_REGISTERED"
    assert res["executable_now"] is True

    status_res = await engine.handle_tool_call(
        "get_trajectory_status",
        {"plan_id": "XAI-PLAN-001"}
    )
    assert "H1_init" in status_res["nodes"]
    assert status_res["is_deadlocked"] is False

@pytest.mark.asyncio
async def test_xai_bridge_sandbox_execute():
    engine = XAIBridgeEngine()
    code = """
import json
print("__METRICS__=" + json.dumps({"resonance": 12.4}))
print("Calculation success")
"""
    res = await engine.handle_tool_call(
        "sandbox_execute",
        {"task_id": "TASK-XAI-EXEC", "code": code}
    )
    assert res["status"] == "SUCCESS"
    assert res["metrics"]["resonance"] == 12.4

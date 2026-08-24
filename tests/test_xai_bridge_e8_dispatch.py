import pytest
from core.bridge.xai_client import XAIBridgeEngine

@pytest.mark.asyncio
async def test_xai_bridge_e8_burst_dispatch():
    engine = XAIBridgeEngine(node_id="TEST-BRIDGE-01")
    
    dispatch_args = {
        "queue_size": 4.5,
        "grad_temp": 3.2,
        "qber": 0.01,
        "channel_loss": 0.02,
        "effective_strain": 3.8,
        "coherence": 0.99,
        "entropy": 0.18,
        "phase_drift": 0.001,
        "budget_sats": 750
    }
    
    res = await engine.handle_tool_call("e8_mesh_burst_dispatch", dispatch_args)
    
    assert res["status"] == "DISPATCH_EXECUTED"
    record = res["record"]
    assert record["budget_sats"] == 750
    assert record["decision"]["status"] == "E8_HIGHWAY_DISPATCHED"
    assert 0 <= record["decision"]["selected_root_index"] < 240

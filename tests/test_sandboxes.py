import pytest
from core.bridge.sandboxes import SubprocessSandbox

@pytest.mark.asyncio
async def test_sandbox_successful_execution():
    sandbox = SubprocessSandbox(timeout_seconds=5.0)
    code = """
import json
print("Computing metrics...")
metrics = {"energy": 1.25, "efficiency": 0.94}
print(f"__METRICS__={json.dumps(metrics)}")
print("Execution Complete")
"""
    res = await sandbox.execute_code(code)
    assert res["status"] == "SUCCESS"
    assert res["exit_code"] == 0
    assert res["metrics"]["energy"] == 1.25
    assert res["metrics"]["efficiency"] == 0.94
    assert "Execution Complete" in res["stdout"]

@pytest.mark.asyncio
async def test_sandbox_syntax_and_runtime_error_capture():
    sandbox = SubprocessSandbox(timeout_seconds=5.0)
    code = """
raise ValueError("Explicit invariant violation in worker script.")
"""
    res = await sandbox.execute_code(code)
    assert res["status"] == "FAILED"
    assert res["exit_code"] != 0
    assert "ValueError" in res["stderr"]

@pytest.mark.asyncio
async def test_sandbox_timeout_termination():
    sandbox = SubprocessSandbox(timeout_seconds=0.5)
    code = """
import time
time.sleep(2.0)
print("Should not be reached")
"""
    res = await sandbox.execute_code(code)
    assert res["status"] == "TIMEOUT"
    assert res["exit_code"] == -1
    assert "timed out" in res["stderr"]

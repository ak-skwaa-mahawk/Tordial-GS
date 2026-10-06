"""Unit tests for failover event recorder."""

from unittest.mock import patch
from core.mesh.failover_logger import FailoverLogger

@patch("core.mesh.cloud_offload.CloudOffloadEngine.put_state")
def test_record_failover(mock_put):
    mock_put.return_value = {"success": True, "target": "mock_target"}

    logger = FailoverLogger()
    evt = logger.record_failover(
        from_model="gemini-3.5-flash-lite",
        to_model="gemini-3.6-flash",
        reason="HTTP 429 RateLimitExceeded",
        root_index=72
    )

    assert evt["root_index"] == 72
    assert evt["primary_model"] == "gemini-3.5-flash-lite"
    assert evt["escalated_model"] == "gemini-3.6-flash"
    assert "timestamp" in evt
    mock_put.assert_called_once()

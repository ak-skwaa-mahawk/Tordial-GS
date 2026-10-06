"""Unit tests for failover event recorder with cooldown suppression."""

from unittest.mock import patch
from core.mesh.failover_logger import FailoverLogger

@patch("core.mesh.cloud_offload.CloudOffloadEngine.put_state")
def test_record_failover_and_cooldown(mock_put):
    mock_put.return_value = {"success": True, "target": "mock_target"}

    logger = FailoverLogger()
    
    # 1. First event records normally
    evt1 = logger.record_failover(
        from_model="gemini-3.5-flash-lite",
        to_model="gemini-3.6-flash",
        reason="HTTP 429 RateLimitExceeded",
        root_index=72
    )
    assert evt1["suppressed"] is False
    assert mock_put.call_count == 1

    # 2. Immediate duplicate event is suppressed
    evt2 = logger.record_failover(
        from_model="gemini-3.5-flash-lite",
        to_model="gemini-3.6-flash",
        reason="HTTP 429 RateLimitExceeded",
        root_index=72
    )
    assert evt2["suppressed"] is True
    assert mock_put.call_count == 1  # No additional upload

    # 3. Different root index records normally
    evt3 = logger.record_failover(
        from_model="gemini-3.5-flash-lite",
        to_model="gemini-3.6-flash",
        reason="HTTP 429 RateLimitExceeded",
        root_index=120
    )
    assert evt3["suppressed"] is False
    assert mock_put.call_count == 2

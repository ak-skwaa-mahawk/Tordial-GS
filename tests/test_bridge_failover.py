"""Unit tests for GeminiBridge automated failover alerting."""

import os
from unittest.mock import patch, MagicMock
from core.mesh.gemini_bridge import GeminiBridge

@patch.dict(os.environ, {"GEMINI_API_KEY": "mock_api_key"})
@patch("core.mesh.failover_logger.FailoverLogger.record_failover")
@patch("urllib.request.urlopen")
def test_bridge_cascade_records_failover(mock_urlopen, mock_record):
    # First model fails (urllib raises Exception), second model succeeds
    first_failure = MagicMock()
    first_failure.side_effect = Exception("HTTP 429 Too Many Requests")

    success_resp = MagicMock()
    success_resp.status = 200
    success_resp.read.return_value = b'{"candidates":[{"content":{"parts":[{"text":"STATUS: ROUTE_STABLE"}]}}]}'
    success_resp.__enter__.return_value = success_resp

    mock_urlopen.side_effect = [Exception("HTTP 429"), success_resp]

    bridge = GeminiBridge()
    res = bridge.query(prompt="Evaluate metric", root_index=72)

    assert res["success"] is True
    assert res["model"] == "gemini-3.6-flash"
    assert mock_record.call_count == 1
    call_args = mock_record.call_args[1]
    assert call_args["from_model"] == "gemini-3.5-flash-lite"
    assert call_args["to_model"] == "gemini-3.6-flash"
    assert call_args["root_index"] == 72

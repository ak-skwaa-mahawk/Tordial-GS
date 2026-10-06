import json
import pytest
from unittest.mock import patch, MagicMock
from core.mesh.kimi_bridge import KimiBridge


def test_kimi_bridge_init_missing_key():
    with patch.dict("os.environ", {}, clear=True):
        bridge = KimiBridge(api_key="")
        with pytest.raises(ValueError, match="MOONSHOT_API_KEY is not configured"):
            bridge.query("test prompt")


def test_kimi_bridge_mock_query_success():
    bridge = KimiBridge(api_key="mock_key")
    mock_payload = {
        "choices": [{"message": {"content": "Validation: PASS"}}],
        "usage": {"total_tokens": 42},
        "model": "moonshot-v1-8k",
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = bridge.query("Test input")
        assert res["success"] is True
        assert res["content"] == "Validation: PASS"
        assert res["tokens_used"] == 42

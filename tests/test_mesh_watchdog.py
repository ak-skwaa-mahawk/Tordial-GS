from unittest.mock import patch
from scripts.mesh_watchdog import check_server_health

def test_watchdog_health_probe():
    with patch("urllib.request.urlopen") as mock_url:
        mock_url.return_value.__enter__.return_value.status = 200
        result = check_server_health(timeout=2.0)
        assert result is True

import pytest
from scripts.mesh_watchdog import check_server_health

def test_watchdog_health_probe():
    # Since the server is running on port 8080, health probe should return True
    result = check_server_health(timeout=2.0)
    assert result is True

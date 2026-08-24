import pytest
from scripts.mesh_bridge_daemon import WS_HOST, WS_PORT, UDP_PORT

def test_bridge_defaults():
    assert WS_HOST == "127.0.0.1"
    assert WS_PORT == 8765
    assert UDP_PORT == 9999

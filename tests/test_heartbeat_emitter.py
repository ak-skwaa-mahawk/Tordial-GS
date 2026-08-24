import pytest
from scripts.peer_heartbeat_emitter import PEERS, TARGET_URL

def test_heartbeat_emitter_config():
    assert len(PEERS) == 6
    assert "HEADSCALE-ALPHA" in PEERS
    assert "GAMMA" in PEERS
    assert "8080" in TARGET_URL

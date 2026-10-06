"""Unit tests for PeerReceiver rate limiting and queue management."""

from core.mesh.peer_telemetry_receiver import PeerReceiver

def test_receiver_token_bucket_limit():
    receiver = PeerReceiver()
    receiver.tokens = 2.0
    
    # First 2 packets allowed
    assert receiver._allow_packet() is True
    assert receiver._allow_packet() is True
    
    # Immediate 3rd packet rejected
    assert receiver._allow_packet() is False
    assert receiver.tokens < 1.0

def test_receiver_token_bucket_refill():
    receiver = PeerReceiver()
    receiver.tokens = 0.0
    receiver.last_refill -= 0.1  # 100ms prior at 100 tokens/sec yields 10 tokens
    
    assert receiver._allow_packet() is True
    assert receiver.tokens >= 8.0

"""Unit tests for outer envelope unwrapping and legacy fallback."""

from core.mesh.crypto_envelope import sign_packet, verify_packet

def test_enveloped_packet_verification():
    raw = {"root_index": 120, "phase_drift": 0.0, "lyapunov": -6.992}
    signed = sign_packet(raw)
    envelope = {
        "signed_packet": signed,
        "transit_metrics": {"transit_delay_ms": 1.45, "rx_epoch": 1700000000.0}
    }

    # Verify unwrapping logic matches audit_mesh_health.py
    pkt = envelope.get("signed_packet", envelope)
    is_valid, payload = verify_packet(pkt)

    assert is_valid is True
    assert payload["root_index"] == 120
    assert payload["phase_drift"] == 0.0

def test_legacy_flat_packet_fallback():
    raw = {"root_index": 48, "phase_drift": 0.0, "lyapunov": -6.992}
    signed = sign_packet(raw)

    # Flat without outer envelope wrapper
    pkt = signed.get("signed_packet", signed)
    is_valid, payload = verify_packet(pkt)

    assert is_valid is True
    assert payload["root_index"] == 48

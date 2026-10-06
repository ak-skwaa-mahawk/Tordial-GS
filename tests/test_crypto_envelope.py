"""Unit tests for HMAC-SHA256 cryptographic envelope verification."""

import pytest
from core.mesh.crypto_envelope import sign_packet, verify_packet

def test_sign_and_verify_valid():
    raw = {"root_index": 48, "phase_drift": 0.0, "lyapunov": -6.992}
    signed = sign_packet(raw)
    assert "sig" in signed
    assert isinstance(signed["sig"], str)
    assert len(signed["sig"]) == 64

    is_valid, payload = verify_packet(signed)
    assert is_valid is True
    assert payload == raw

def test_verify_tampered_payload():
    raw = {"root_index": 48, "phase_drift": 0.0, "lyapunov": -6.992}
    signed = sign_packet(raw)
    # Tamper with metric post-signing
    signed["phase_drift"] = 0.55555

    is_valid, _ = verify_packet(signed)
    assert is_valid is False

def test_verify_bad_signature():
    packet = {
        "root_index": 12,
        "phase_drift": 0.0,
        "lyapunov": -6.992,
        "sig": "0000000000000000000000000000000000000000000000000000000000000000"
    }
    is_valid, _ = verify_packet(packet)
    assert is_valid is False

def test_verify_missing_signature():
    raw = {"root_index": 48, "phase_drift": 0.0, "lyapunov": -6.992}
    is_valid, _ = verify_packet(raw)
    assert is_valid is False

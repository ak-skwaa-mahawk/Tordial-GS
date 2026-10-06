"""HMAC-SHA256 Packet Signer and Verifier for Sovereign Mesh Packets."""

import hmac
import hashlib
import json
import os

SHARED_MESH_KEY = os.environ.get("TORDIAL_HMAC_KEY", "sovereign_mesh_secret_lattice_k8").encode("utf-8")

def sign_packet(payload: dict) -> dict:
    """Signs a packet payload and attaches signature + timestamp."""
    clean = {k: v for k, v in payload.items() if k != "sig"}
    serialized = json.dumps(clean, sort_keys=True).encode("utf-8")
    sig = hmac.new(SHARED_MESH_KEY, serialized, hashlib.sha256).hexdigest()
    packet = dict(clean)
    packet["sig"] = sig
    return packet

def verify_packet(packet: dict) -> tuple[bool, dict]:
    """Validates signature integrity. Returns (is_valid, payload)."""
    received_sig = packet.get("sig", "")
    clean = {k: v for k, v in packet.items() if k != "sig"}
    expected_sig = hmac.new(SHARED_MESH_KEY, json.dumps(clean, sort_keys=True).encode("utf-8"), hashlib.sha256).hexdigest()
    if hmac.compare_digest(received_sig, expected_sig):
        return True, clean
    return False, clean

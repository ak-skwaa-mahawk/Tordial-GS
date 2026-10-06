"""Unit tests for transit latency and dispersion metric utilities."""

import time
from core.mesh.telemetry_metrics import create_telemetry_payload, enrich_transit_metrics

def test_create_telemetry_payload():
    before = time.time()
    p = create_telemetry_payload(root_index=12)
    after = time.time()

    assert p["root_index"] == 12
    assert p["phase_drift"] == 0.0
    assert p["lyapunov"] == -6.992
    assert before <= p["tx_epoch"] <= after

def test_enrich_transit_metrics():
    tx = time.time() - 0.025  # Simulated 25ms transit
    raw = {"root_index": 48, "tx_epoch": tx}
    enriched = enrich_transit_metrics(raw)

    assert "rx_epoch" in enriched
    assert "transit_delay_ms" in enriched
    assert enriched["transit_delay_ms"] >= 20.0

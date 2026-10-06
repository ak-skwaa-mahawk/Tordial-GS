"""Transit Latency and Dispersion Metric Calculators for Mesh Packets."""

import time

def create_telemetry_payload(root_index: int, phase_drift: float = 0.0, lyapunov: float = -6.992) -> dict:
    """Constructs nominal signed packet payload with outbound epoch."""
    return {
        "root_index": root_index,
        "phase_drift": phase_drift,
        "lyapunov": lyapunov,
        "tx_epoch": time.time()
    }

def enrich_transit_metrics(payload: dict) -> dict:
    """Appends rx_epoch and calculate one-way link transit delay."""
    rx_epoch = time.time()
    tx_epoch = payload.get("tx_epoch", rx_epoch)
    rtt_ms = max(0.0, (rx_epoch - tx_epoch) * 1000.0)
    
    enriched = dict(payload)
    enriched["rx_epoch"] = rx_epoch
    enriched["transit_delay_ms"] = round(rtt_ms, 3)
    return enriched

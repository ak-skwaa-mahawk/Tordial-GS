"""Jitter and Dispersion Statistical Analyzer for Mesh Telemetry."""

import math

def compute_jitter_stats(delays_ms: list[float]) -> dict:
    """Computes mean, sample standard deviation (jitter), min, and max delay."""
    if not delays_ms:
        return {
            "sample_count": 0,
            "mean_delay_ms": 0.0,
            "jitter_ms": 0.0,
            "min_delay_ms": 0.0,
            "max_delay_ms": 0.0
        }

    n = len(delays_ms)
    mean = sum(delays_ms) / n
    variance = sum((x - mean) ** 2 for x in delays_ms) / (n - 1) if n > 1 else 0.0
    jitter = math.sqrt(variance)

    return {
        "sample_count": n,
        "mean_delay_ms": round(mean, 3),
        "jitter_ms": round(jitter, 3),
        "min_delay_ms": round(min(delays_ms), 3),
        "max_delay_ms": round(max(delays_ms), 3)
    }

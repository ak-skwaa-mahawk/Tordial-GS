"""Statistical Dispersion Anomaly and Trend Spike Detector."""

import math

def detect_dispersion_spike(current_jitter: float, historical_jitters: list[float], threshold_sigma: float = 2.5) -> dict:
    """Evaluates whether current transport jitter represents a statistically significant anomaly."""
    if len(historical_jitters) < 3:
        return {
            "is_anomaly": False,
            "z_score": 0.0,
            "baseline_mean": current_jitter,
            "baseline_std": 0.0,
            "reason": "Insufficient historical window"
        }

    n = len(historical_jitters)
    mean = sum(historical_jitters) / n
    variance = sum((x - mean) ** 2 for x in historical_jitters) / (n - 1)
    std = math.sqrt(variance)

    if std == 0.0:
        is_spike = current_jitter > (mean * 1.5)
        return {
            "is_anomaly": is_spike,
            "z_score": 999.0 if is_spike else 0.0,
            "baseline_mean": round(mean, 4),
            "baseline_std": 0.0,
            "reason": "Zero historical variance" if not is_spike else "Step deviation above static baseline"
        }

    z_score = (current_jitter - mean) / std
    is_anomaly = z_score >= threshold_sigma

    return {
        "is_anomaly": is_anomaly,
        "z_score": round(z_score, 3),
        "baseline_mean": round(mean, 4),
        "baseline_std": round(std, 4),
        "reason": f"Jitter excursion ({z_score:.2f}σ >= {threshold_sigma}σ)" if is_anomaly else "Nominal dispersion"
    }

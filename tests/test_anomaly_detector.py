"""Unit tests for statistical dispersion spike detector."""

from core.mesh.anomaly_detector import detect_dispersion_spike

def test_anomaly_insufficient_samples():
    res = detect_dispersion_spike(0.08, [0.07, 0.08])
    assert res["is_anomaly"] is False
    assert res["reason"] == "Insufficient historical window"

def test_anomaly_nominal_jitter():
    history = [0.075, 0.080, 0.078, 0.082, 0.079]
    res = detect_dispersion_spike(0.081, history)
    assert res["is_anomaly"] is False
    assert res["z_score"] < 2.5

def test_anomaly_detected_on_spike():
    history = [0.075, 0.080, 0.078, 0.082, 0.079]
    # Injected jitter spike to 0.45ms (well above 0.08ms baseline)
    res = detect_dispersion_spike(0.450, history)
    assert res["is_anomaly"] is True
    assert res["z_score"] > 2.5
    assert "Jitter excursion" in res["reason"]

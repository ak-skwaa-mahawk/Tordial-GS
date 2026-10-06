"""Unit tests for jitter and dispersion analyzer."""

import pytest
from core.mesh.jitter_analyzer import compute_jitter_stats

def test_compute_jitter_stats_empty():
    stats = compute_jitter_stats([])
    assert stats["sample_count"] == 0
    assert stats["mean_delay_ms"] == 0.0
    assert stats["jitter_ms"] == 0.0

def test_compute_jitter_stats_single():
    stats = compute_jitter_stats([1.5])
    assert stats["sample_count"] == 1
    assert stats["mean_delay_ms"] == 1.5
    assert stats["jitter_ms"] == 0.0

def test_compute_jitter_stats_multiple():
    delays = [0.4, 0.6, 0.5, 0.5]
    stats = compute_jitter_stats(delays)
    assert stats["sample_count"] == 4
    assert stats["mean_delay_ms"] == 0.5
    assert stats["min_delay_ms"] == 0.4
    assert stats["max_delay_ms"] == 0.6
    assert stats["jitter_ms"] == pytest.approx(0.082, abs=1e-3)

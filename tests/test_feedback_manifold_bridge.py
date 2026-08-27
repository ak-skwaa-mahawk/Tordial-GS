import pytest
import numpy as np
from core.mesh.feedback_manifold_bridge import FeedbackManifoldBridge

def test_bridge_telemetry_shape():
    bridge = FeedbackManifoldBridge(num_nodes=8)
    vec = bridge.generate_coherent_telemetry(dt=0.05)
    assert isinstance(vec, np.ndarray)
    assert len(vec) == 8
    assert vec[5] > 0.0  # Coherence component

import pytest
import numpy as np
from core.mesh.router import E8RootDispatcher

def test_qber_and_channel_loss_attenuation():
    dispatcher = E8RootDispatcher()
    queues = np.zeros(240, dtype=float)

    # Clean quantum channel: low QBER (0.01), low Loss (0.01)
    clean_state = np.array([4.0, 3.0, 0.01, 0.01, 3.5, 0.98, 0.2, 0.002])
    weights_clean = dispatcher.compute_dispatch_weights(clean_state, queues)

    # Degraded quantum channel: high QBER (0.15 > 0.11 crit), high Loss (0.4)
    degraded_state = np.array([4.0, 3.0, 0.15, 0.40, 3.5, 0.98, 0.2, 0.002])
    weights_degraded = dispatcher.compute_dispatch_weights(degraded_state, queues)

    max_clean = np.max(weights_clean)
    max_degraded = np.max(weights_degraded)

    assert max_clean > 0.0
    assert max_degraded > 0.0
    # Degraded weights must be significantly attenuated relative to clean channel
    assert max_degraded < (max_clean * 0.5)

def test_zero_weight_on_extreme_noise():
    dispatcher = E8RootDispatcher()
    queues = np.zeros(240, dtype=float)

    extreme_state = np.array([4.0, 3.0, 0.80, 2.50, 3.5, 0.98, 0.2, 0.002])
    weights_extreme = dispatcher.compute_dispatch_weights(extreme_state, queues)

    # Near complete decay of weights under destructive channel noise
    assert np.max(weights_extreme) < 1e-4

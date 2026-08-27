import sys
from pathlib import Path
import numpy as np

# Dynamically link Feedback_processor_theory workspace
FEEDBACK_ROOT = Path.home() / "Feedback_processor_theory"
if str(FEEDBACK_ROOT) not in sys.path:
    sys.path.insert(0, str(FEEDBACK_ROOT))

try:
    from core.phase_engine import ContinuousFeedbackProcessor
    from core.harmonic_scaling import HarmonicScaleFeedback
except ImportError:
    ContinuousFeedbackProcessor = None
    HarmonicScaleFeedback = None

class FeedbackManifoldBridge:
    def __init__(self, num_nodes: int = 8):
        if ContinuousFeedbackProcessor and HarmonicScaleFeedback:
            self.phase_engine = ContinuousFeedbackProcessor(num_nodes=num_nodes, coupling_strength=2.0)
            self.harmonic_engine = HarmonicScaleFeedback(num_scales=num_nodes)
        else:
            self.phase_engine = None
            self.harmonic_engine = None

    def generate_coherent_telemetry(self, dt: float = 0.02) -> np.ndarray:
        """
        Evolves continuous wave state and projects an 8D telemetry vector
        weighted by the instantaneous phase-lock coherence.
        """
        if not self.phase_engine or not self.harmonic_engine:
            # Fallback 8D baseline
            return np.array([4.5, 3.2, 0.01, 0.01, 3.5, 0.99, 0.1, 0.001], dtype=np.float64)

        self.phase_engine.step_continuous_flow(dt=dt)
        coherence = self.phase_engine.order_parameter()
        self.harmonic_engine.evolve_field(dt=dt, feedback_drive=coherence)

        phases = self.harmonic_engine.scale_phases[:8]
        # Construct 8D vector from continuous wave features
        telemetry_8d = np.zeros(8, dtype=np.float64)
        telemetry_8d[0] = 4.0 + (coherence * 1.5)           # Latency proxy
        telemetry_8d[1] = 2.0 + np.sin(phases[0])            # Queue proxy
        telemetry_8d[2] = 0.01 * (1.0 - coherence * 0.5)     # Loss proxy
        telemetry_8d[3] = 0.01 + 0.005 * np.cos(phases[1])   # Jitter proxy
        telemetry_8d[4] = 3.0 + np.abs(np.sin(phases[2]))    # Energy proxy
        telemetry_8d[5] = float(np.clip(coherence, 0.1, 0.999)) # Phase Coherence
        telemetry_8d[6] = 0.1 / (1.0 + coherence)            # Drift proxy
        telemetry_8d[7] = 0.001 * (1.0 + np.sin(phases[3]))  # Phase error

        return telemetry_8d

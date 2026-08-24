import pytest
import numpy as np
from core.mesh.e8_visualizer import E8TerminalVisualizer

def test_e8_heat_grid_rendering():
    viz = E8TerminalVisualizer()
    queues = np.zeros(240, dtype=float)
    queues[0] = 5.0
    queues[239] = 2.5
    
    output = viz.render_e8_heat_grid(queues)
    assert "240 E8 ROOT HIGHWAY ALLOCATION MAP" in output
    assert len(output.splitlines()) == 16  # Title + 15 rows

def test_tba_spectrum_rendering():
    viz = E8TerminalVisualizer()
    output = viz.render_tba_queue_spectrum(T_eff=1.2)
    
    assert "TBA STEADY-STATE QUEUE SPECTRUM" in output
    assert "Species 1" in output
    assert "Species 8" in output

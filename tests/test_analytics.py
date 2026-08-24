import pytest
from scripts.analyze_mesh_volume import analyze_mesh_volume

def test_analyze_mesh_volume(capsys):
    analyze_mesh_volume()
    captured = capsys.readouterr()
    assert "TORDIAL E8 MESH ROUTING & FEE ANALYTICS" in captured.out
    assert "Total Settled Transactions" in captured.out

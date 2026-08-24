import pytest
import json
from pathlib import Path

def test_grafana_dashboard_schema():
    path = Path(__file__).resolve().parent.parent / "grafana_dashboard_e8_mesh.json"
    assert path.exists()
    
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert data["uid"] == "tordial-e8-mesh"
    assert data["title"] == "Tordial E8 Sovereign Mesh Operations"
    assert len(data["panels"]) >= 6
    
    panel_titles = [p.get("title") for p in data["panels"]]
    assert "Active Mesh Peers" in panel_titles
    assert "Thermodynamic Bethe Ansatz Queue Profile" in panel_titles

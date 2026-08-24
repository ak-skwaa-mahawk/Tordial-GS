import pytest
import json
import threading
import time
from http.client import HTTPConnection
from http.server import HTTPServer
from core.mesh.server import SovereignMeshHTTPHandler

TEST_PORT = 8998

@pytest.fixture(scope="module", autouse=True)
def start_test_server():
    server = HTTPServer(("127.0.0.1", TEST_PORT), SovereignMeshHTTPHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.1)
    yield
    server.shutdown()
    server.server_close()

def make_request(method: str, path: str, body: dict = None):
    conn = HTTPConnection("127.0.0.1", TEST_PORT, timeout=2.0)
    headers = {"Content-Type": "application/json"} if body else {}
    body_data = json.dumps(body) if body else None
    conn.request(method, path, body=body_data, headers=headers)
    res = conn.getresponse()
    raw = res.read().decode("utf-8")
    data = json.loads(raw) if raw else {}
    conn.close()
    return res.status, data

def test_health_endpoint():
    status, data = make_request("GET", "/health")
    assert status == 200
    assert data["status"] == "HEALTHY"
    assert "node_id" in data

def test_e8_highways_endpoint():
    status, data = make_request("GET", "/api/v1/e8/highways")
    assert status == 200
    assert data["total_highways"] == 240
    assert len(data["queue_depths"]) == 240

def test_tba_spectrum_endpoint():
    status, data = make_request("GET", "/api/v1/e8/tba_spectrum?t_eff=1.5")
    assert status == 200
    assert len(data["species_masses"]) == 8
    assert len(data["steady_state_queue_depths"]) == 8
    assert data["total_queue_load"] > 0

def test_dispatch_burst_endpoint():
    payload = {
        "queue_size": 4.5,
        "grad_temp": 3.2,
        "qber": 0.01,
        "channel_loss": 0.02,
        "effective_strain": 3.8,
        "coherence": 0.99,
        "entropy": 0.15,
        "phase_drift": 0.001,
        "budget_sats": 500
    }
    status, data = make_request("POST", "/api/v1/e8/dispatch", body=payload)
    assert status == 200
    assert data["dispatch"]["decision"]["status"] == "E8_HIGHWAY_DISPATCHED"
    assert data["settlement"]["status"] == "SETTLED"

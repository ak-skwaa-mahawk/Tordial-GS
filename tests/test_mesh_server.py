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
    content_type = res.getheader("Content-Type", "")
    data = json.loads(raw) if "json" in content_type else raw
    conn.close()
    return res.status, data

def test_health_endpoint():
    status, data = make_request("GET", "/health")
    assert status == 200
    assert data["status"] == "HEALTHY"
    assert "healthy_peers_count" in data

def test_metrics_endpoint():
    status, raw_text = make_request("GET", "/metrics")
    assert status == 200
    assert "tordial_mesh_healthy_peers" in raw_text
    assert "tordial_e8_active_highways" in raw_text

def test_peer_heartbeat_endpoint():
    status, data = make_request("POST", "/api/v1/peer/heartbeat", body={"peer_id": "HEADSCALE-ALPHA"})
    assert status == 200
    assert data["status"] == "HEARTBEAT_ACK"
    assert "HEADSCALE-ALPHA" in data["healthy_peers"]

def test_dispatch_burst_with_failover_status():
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
    assert data["dispatch"]["decision"]["failover_mode"] in ["DISTRIBUTED", "LOCAL_FALLBACK"]

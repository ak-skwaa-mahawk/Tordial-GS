import pytest
import json
import threading
import time
from unittest.mock import patch
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

def make_request(method: str, path: str, body: dict = None, headers: dict = None):
    conn = HTTPConnection("127.0.0.1", TEST_PORT, timeout=2.0)
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    body_data = json.dumps(body) if body else None
    conn.request(method, path, body=body_data, headers=req_headers)
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

def test_peer_heartbeat_endpoint():
    status, data = make_request("POST", "/api/v1/peer/heartbeat", body={"peer_id": "HEADSCALE-ALPHA"})
    assert status == 200
    assert data["status"] == "HEARTBEAT_ACK"

def test_dispatch_burst_free_tier():
    payload = {"budget_sats": 500, "require_payment": False}
    status, data = make_request("POST", "/api/v1/e8/dispatch", body=payload)
    assert status == 200
    assert data["payment_verified"] is False
    assert "dispatch" in data

def test_dispatch_burst_missing_payment_required():
    payload = {"budget_sats": 500, "require_payment": True}
    status, data = make_request("POST", "/api/v1/e8/dispatch", body=payload)
    assert status == 402
    assert data["error"] == "PAYMENT_REQUIRED"

@patch("core.mesh.server.verify_xrpl_payment")
def test_dispatch_burst_payment_success(mock_verify):
    mock_verify.return_value = True
    payload = {"budget_sats": 500, "require_payment": True, "xrpl_tx_hash": "A"*64}
    status, data = make_request("POST", "/api/v1/e8/dispatch", body=payload)
    assert status == 200
    assert data["payment_verified"] is True

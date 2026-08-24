import pytest
import socket
import json
import base64
import threading
import time
from http.server import HTTPServer
from core.mesh.server import SovereignMeshHTTPHandler

WS_TEST_PORT = 8997

@pytest.fixture(scope="module", autouse=True)
def run_ws_server():
    server = HTTPServer(("127.0.0.1", WS_TEST_PORT), SovereignMeshHTTPHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield
    server.shutdown()
    server.server_close()

def test_raw_websocket_handshake_and_frame():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", WS_TEST_PORT))
    
    key = base64.b64encode(b"0123456789abcdef").decode("utf-8")
    req = (
        f"GET /ws/telemetry HTTP/1.1\r\n"
        f"Host: 127.0.0.1:{WS_TEST_PORT}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode("utf-8"))
    
    # Read HTTP/1.1 101 Switching Protocols response
    headers = b""
    while b"\r\n\r\n" not in headers:
        headers += sock.recv(1024)
    assert b"101" in headers
    assert b"Sec-WebSocket-Accept" in headers

    # Read first WebSocket data frame
    frame_header = sock.recv(2)
    assert frame_header[0] == 0x81  # Text frame
    payload_len = frame_header[1] & 0x7F
    
    if payload_len == 126:
        ext_len = sock.recv(2)
        payload_len = int.from_bytes(ext_len, "big")
        
    data = b""
    while len(data) < payload_len:
        data += sock.recv(payload_len - len(data))
        
    parsed = json.loads(data.decode("utf-8"))
    assert "species_masses" not in parsed or "queue_depths" in parsed
    assert "node_id" in parsed
    assert "total_queue_load" in parsed
    sock.close()

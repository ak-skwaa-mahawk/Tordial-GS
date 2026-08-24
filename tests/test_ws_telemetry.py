import pytest
import socket
import json
import base64
import struct
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
    sock.settimeout(5.0)
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

    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(1024)
        if not chunk:
            break
        buf += chunk

    assert b"101" in buf
    assert b"Sec-WebSocket-Accept" in buf

    header_end = buf.find(b"\r\n\r\n") + 4
    buf = buf[header_end:]

    def read_exact(n):
        nonlocal buf
        while len(buf) < n:
            chunk = sock.recv(1024)
            if not chunk:
                raise EOFError("Socket closed")
            buf += chunk
        res = buf[:n]
        buf = buf[n:]
        return res

    hdr = read_exact(2)
    assert hdr[0] == 0x81  # FIN + Text Frame opcode

    length = hdr[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", read_exact(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", read_exact(8))[0]

    payload = read_exact(length)
    parsed = json.loads(payload.decode("utf-8"))

    assert "node_id" in parsed
    assert "total_queue_load" in parsed
    assert "queue_depths" in parsed
    sock.close()

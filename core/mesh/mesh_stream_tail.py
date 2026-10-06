"""Sovereign Real-Time Mesh Telemetry Stream Viewer.

Tails live UDP loopback telemetry packets directly, displaying transit delay,
HMAC authenticity, phase drift, and Lyapunov convergence in real time.
"""

import socket
import json
import sys
import os

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))
from core.mesh.crypto_envelope import verify_packet
from core.mesh.telemetry_metrics import enrich_transit_metrics

LISTEN_PORT = 18889  # Broadcast or mirror port

def stream_listener(port: int = 18888):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Enable address reuse for non-intrusive sniffing
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except AttributeError:
        pass

    try:
        sock.bind(("127.0.0.1", port))
    except Exception as e:
        print(f"[-] Binding directly to :{port} failed ({e}). Run in passive spy mode.")
        return

    print(f"[*] Sovereign Mesh Telemetry Stream listening on 127.0.0.1:{port}...")
    print(f"{'ROOT':<6} | {'STATUS':<7} | {'DRIFT (rad)':<12} | {'LYAPUNOV (λ)':<14} | {'DELAY (ms)':<10}")
    print("-" * 62)

    try:
        while True:
            data, _ = sock.recvfrom(4096)
            try:
                pkt = json.loads(data.decode("utf-8"))
            except Exception:
                continue

            valid, payload = verify_packet(pkt)
            meta = enrich_transit_metrics(payload)

            root = payload.get("root_index", "?")
            drift = payload.get("phase_drift", 0.0)
            lyap = payload.get("lyapunov", -6.992)
            delay = meta.get("transit_delay_ms", 0.0)
            status = "VALID" if valid else "INVALID"

            print(f"#{root:<5} | {status:<7} | {drift:<12.5f} | {lyap:<14.4f} | {delay:<10.3f}")
    except KeyboardInterrupt:
        print("\n[*] Stopping stream.")
    finally:
        sock.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18888
    stream_listener(port)

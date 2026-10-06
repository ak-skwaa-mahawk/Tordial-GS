"""Sovereign Peer Telemetry Receiver and Autonomous Arbiter.

Listens for incoming peer metric packets over loopback UDP. Evaluates anomalous
metric drift through GeminiBridge and offloads raw events directly to Google Drive.
"""

import socket
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))

from core.mesh.e8_router import E8GeodesicRouter
from core.mesh.autonomous_healer import heal_deviant_vector
from core.mesh.cloud_offload import CloudOffloadEngine

LISTEN_PORT = 18888
BUFFER_SIZE = 4096

def start_receiver():
    router = E8GeodesicRouter()
    offloader = CloudOffloadEngine()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", LISTEN_PORT))
    print(f"[+] Peer Telemetry Receiver bound to 127.0.0.1:{LISTEN_PORT}")

    try:
        while True:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            try:
                packet = json.loads(data.decode("utf-8"))
            except Exception:
                continue

            root_idx = packet.get("root_index", 12)
            phase_drift = packet.get("phase_drift", 0.0)
            lyapunov = packet.get("lyapunov", -6.992)

            print(f"[*] Packet from {addr}: Root #{root_idx} | Drift={phase_drift} | λ={lyapunov}")

            # Offload raw packet event to vault
            offloader.put_state(f"telemetry/packets/last_packet_root_{root_idx}.json", packet)

            # Gate execution: only invoke Gemini reasoning when metrics breach envelope
            if abs(phase_drift) > 0.001 or lyapunov > -1.0:
                print(f"[!] Breach detected on Root #{root_idx}. Triggering router...")
                eval_res = router.evaluate_vector(root_idx, phase_drift, lyapunov)
                if "ROUTE_DEVIANT" in eval_res.get("verdict", "").upper():
                    print(f"[!] Deviance certified. Running autonomous healer...")
                    heal_deviant_vector(root_idx)
            else:
                print(f"[+] Root #{root_idx} within sovereign limits. No re-route required.")

    except KeyboardInterrupt:
        print("\n[*] Shutting down receiver.")
    finally:
        sock.close()

if __name__ == "__main__":
    start_receiver()

"""Sovereign Peer Telemetry Receiver and Autonomous Arbiter.

Listens for signed peer metric packets over loopback UDP. Verifies cryptographic
signatures, enriches transit delay metrics in a non-destructive outer envelope,
evaluates metric drift through GeminiBridge, and streams verified raw events to Google Drive.
"""

import socket
import json
import os
import sys
import queue
import threading

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))

from core.mesh.e8_router import E8GeodesicRouter
from core.mesh.autonomous_healer import heal_deviant_vector
from core.mesh.cloud_offload import CloudOffloadEngine
from core.mesh.crypto_envelope import verify_packet
from core.mesh.telemetry_metrics import enrich_transit_metrics

LISTEN_PORT = 18888
BUFFER_SIZE = 4096

class PeerReceiver:
    def __init__(self):
        self.router = E8GeodesicRouter()
        self.offloader = CloudOffloadEngine()
        self.upload_queue = queue.Queue()
        self.running = True
        self.worker = threading.Thread(target=self._vault_worker, daemon=True)
        self.worker.start()

    def _vault_worker(self):
        while self.running or not self.upload_queue.empty():
            try:
                target_path, payload = self.upload_queue.get(timeout=0.5)
                self.offloader.put_state(target_path, payload)
                self.upload_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[-] Vault worker exception: {e}")

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", LISTEN_PORT))
        print(f"[+] Authenticated Peer Receiver bound to 127.0.0.1:{LISTEN_PORT}")

        try:
            while self.running:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                try:
                    packet = json.loads(data.decode("utf-8"))
                except Exception:
                    continue

                valid, payload = verify_packet(packet)
                if not valid:
                    print(f"[-] FORGED PACKET from {addr}. Signature check failed. Dropping.")
                    continue

                enriched_meta = enrich_transit_metrics(payload)
                delay_ms = enriched_meta.get("transit_delay_ms", 0.0)

                root_idx = payload.get("root_index", 12)
                phase_drift = payload.get("phase_drift", 0.0)
                lyapunov = payload.get("lyapunov", -6.992)

                print(f"[*] Valid packet from {addr}: Root #{root_idx} | Drift={phase_drift} | λ={lyapunov} | Delay={delay_ms}ms")

                # Preserve verified packet intact alongside transit metadata
                vault_record = {
                    "signed_packet": packet,
                    "transit_metrics": {
                        "rx_epoch": enriched_meta["rx_epoch"],
                        "transit_delay_ms": delay_ms
                    }
                }
                target = f"telemetry/packets/last_packet_root_{root_idx}.json"
                self.upload_queue.put((target, vault_record))

                # Envelope gate
                if abs(phase_drift) > 0.001 or lyapunov > -1.0:
                    print(f"[!] Metric divergence on Root #{root_idx}. Routing verification...")
                    eval_res = self.router.evaluate_vector(root_idx, phase_drift, lyapunov)
                    if "ROUTE_DEVIANT" in eval_res.get("verdict", "").upper():
                        print(f"[!] Deviance confirmed. Running autonomous healer...")
                        heal_deviant_vector(root_idx)
                else:
                    print(f"[+] Root #{root_idx} within sovereign stability envelope.")

        except KeyboardInterrupt:
            print("\n[*] Stopping receiver...")
        finally:
            self.running = False
            sock.close()
            self.upload_queue.join()
            print("[+] Vault sync complete.")

if __name__ == "__main__":
    receiver = PeerReceiver()
    receiver.start()

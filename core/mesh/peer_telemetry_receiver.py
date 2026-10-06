"""Sovereign Peer Telemetry Receiver and Autonomous Arbiter.

Listens for signed peer metric packets over loopback UDP. Verifies cryptographic
signatures, enriches transit delay metrics in a non-destructive outer envelope,
fans out packet replicas to loopback tap (18889), applies token-bucket ingress rate limiting,
dispatches routing evaluations asynchronously, and streams verified raw events to Google Drive.
"""

import socket
import json
import os
import sys
import queue
import threading
import time

sys.path.insert(0, os.path.expanduser("~/Tordial-GS"))

from core.mesh.e8_router import E8GeodesicRouter
from core.mesh.autonomous_healer import heal_deviant_vector
from core.mesh.cloud_offload import CloudOffloadEngine
from core.mesh.crypto_envelope import verify_packet
from core.mesh.telemetry_metrics import enrich_transit_metrics

LISTEN_PORT = 18888
TAP_PORT = 18889
BUFFER_SIZE = 4096
BURST_CAPACITY = 250.0
REFILL_RATE_PER_SEC = 100.0

class PeerReceiver:
    def __init__(self):
        self.router = E8GeodesicRouter()
        self.offloader = CloudOffloadEngine()
        self.upload_queue = queue.Queue(maxsize=1000)
        self.running = True
        self.tap_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Token-bucket rate limiter state
        self.tokens = BURST_CAPACITY
        self.last_refill = time.time()
        self.dropped_packets = 0
        self.processed_packets = 0

        self.worker = threading.Thread(target=self._vault_worker, daemon=True)
        self.worker.start()

    def _allow_packet(self) -> bool:
        now = time.time()
        delta = now - self.last_refill
        self.last_refill = now
        self.tokens = min(BURST_CAPACITY, self.tokens + (delta * REFILL_RATE_PER_SEC))
        
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

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

    def _async_heal(self, root_idx: int, phase_drift: float, lyapunov: float):
        try:
            print(f"[!] Background evaluation active for Root #{root_idx}...")
            eval_res = self.router.evaluate_vector(root_idx, phase_drift, lyapunov)
            if "ROUTE_DEVIANT" in eval_res.get("verdict", "").upper():
                print(f"[!] Deviance confirmed. Running autonomous healer...")
                heal_deviant_vector(root_idx)
        except Exception as e:
            print(f"[-] Healer dispatch error on Root #{root_idx}: {e}")

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("127.0.0.1", LISTEN_PORT))
        print(f"[+] Authenticated Peer Receiver bound to 127.0.0.1:{LISTEN_PORT}")

        try:
            while self.running:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                
                if not self._allow_packet():
                    self.dropped_packets += 1
                    continue

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
                self.processed_packets += 1

                print(f"[*] Valid packet from {addr}: Root #{root_idx} | Drift={phase_drift} | λ={lyapunov} | Delay={delay_ms}ms")

                # Fan-out replicate to tap port for live stream viewers
                try:
                    self.tap_sock.sendto(data, ("127.0.0.1", TAP_PORT))
                except Exception:
                    pass

                # Preserve verified packet intact alongside transit metadata
                vault_record = {
                    "signed_packet": packet,
                    "transit_metrics": {
                        "rx_epoch": enriched_meta["rx_epoch"],
                        "transit_delay_ms": delay_ms
                    }
                }
                target = f"telemetry/packets/last_packet_root_{root_idx}.json"
                try:
                    self.upload_queue.put_nowait((target, vault_record))
                except queue.Full:
                    self.dropped_packets += 1

                # Envelope gate (Async non-blocking dispatch)
                if abs(phase_drift) > 0.001 or lyapunov > -1.0:
                    threading.Thread(
                        target=self._async_heal,
                        args=(root_idx, phase_drift, lyapunov),
                        daemon=True
                    ).start()
                else:
                    print(f"[+] Root #{root_idx} within sovereign stability envelope.")

        except KeyboardInterrupt:
            print("\n[*] Stopping receiver...")
        finally:
            self.running = False
            sock.close()
            self.tap_sock.close()
            self.upload_queue.join()
            print(f"[+] Vault sync complete. (Processed={self.processed_packets}, Dropped={self.dropped_packets})")

if __name__ == "__main__":
    receiver = PeerReceiver()
    receiver.start()

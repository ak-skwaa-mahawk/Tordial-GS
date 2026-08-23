"""Telemetry Emitter: Dispatches manifold invariant metrics to local UDP socket."""
import json
import socket
from typing import Dict, Any

class TelemetryEmitter:
    def __init__(self, host: str = "127.0.0.1", port: int = 9999):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def emit(self, event_type: str, data: Dict[str, Any]):
        payload = {
            "source": "tordial-gs",
            "event": event_type,
            "data": data
        }
        try:
            self.sock.sendto(json.dumps(payload).encode("utf-8"), (self.host, self.port))
        except Exception as exc:
            pass  # Non-blocking telemetry broadcast

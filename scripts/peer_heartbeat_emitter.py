import time
import urllib.request
import json

PEERS = ["TORDIAL-EDGE-02"]
TARGET_URL = "http://127.0.0.1:8080/api/v1/peer/heartbeat"

def emit_heartbeats():
    while True:
        for peer in PEERS:
            try:
                payload = json.dumps({"peer_id": peer}).encode("utf-8")
                req = urllib.request.Request(
                    TARGET_URL,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    pass
            except Exception:
                pass
        time.sleep(10)

if __name__ == "__main__":
    emit_heartbeats()

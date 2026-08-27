#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import time
import json
import urllib.request
import urllib.error
from core.mesh.feedback_manifold_bridge import FeedbackManifoldBridge

ENDPOINT = "http://127.0.0.1:8080/api/v1/e8/dispatch"

def start_continuous_feed():
    print("=" * 60)
    print("🚀 CONTINUOUS HARMONIC BURST INJECTOR ACTIVATED")
    print("=" * 60)
    
    bridge = FeedbackManifoldBridge(num_nodes=8)
    
    while True:
        try:
            vec = bridge.generate_coherent_telemetry(dt=0.03)
            payload = {
                "origin": "TORDIAL-EDGE-01",
                "telemetry": vec.tolist(),
                "budget_sats": 500,
                "require_payment": False
            }
            
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                ENDPOINT,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                coherence = vec[5]
                print(f"[*] Dispatched Burst | Coherence={coherence:.4f} | Status={result.get('status', 'OK')}")
                
        except urllib.error.URLError as e:
            print(f"[!] Endpoint unreachable ({e}), retrying in 3s...")
        except Exception as e:
            print(f"[!] Error: {e}")
            
        time.sleep(2.0)

if __name__ == "__main__":
    start_continuous_feed()

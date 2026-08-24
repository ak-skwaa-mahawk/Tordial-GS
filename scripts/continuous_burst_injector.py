import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import time
import json
import random
import urllib.request
import urllib.error

ENDPOINT = "http://127.0.0.1:8080/api/v1/e8/dispatch"
INTERVAL_SEC = 10.0

def generate_burst_payload() -> dict:
    # Construct an active 8D vector that clears mass gates while keeping phase drift stable
    return {
        "queue_size": round(random.uniform(3.5, 5.0), 3),
        "grad_temp": round(random.uniform(2.8, 3.4), 3),
        "qber": round(random.uniform(0.005, 0.025), 4),
        "channel_loss": round(random.uniform(0.008, 0.030), 4),
        "effective_strain": round(random.uniform(3.2, 4.0), 2),
        "coherence": round(random.uniform(0.97, 0.995), 4),
        "entropy": round(random.uniform(0.10, 0.25), 3),
        "phase_drift": round(random.uniform(-0.004, 0.004), 4),
        "budget_sats": 500
    }

def post_burst(payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    print(f"🚀 [BURST INJECTOR]: Starting continuous loop (interval: {INTERVAL_SEC}s) -> {ENDPOINT}")
    cycle = 0

    while True:
        payload = generate_burst_payload()
        cycle += 1
        try:
            res = post_burst(payload)
            decision = res.get("dispatch", {}).get("decision", {})
            settlement = res.get("settlement", {})
            
            root_idx = decision.get("selected_root_index", "N/A")
            weight = decision.get("dispatch_weight", 0.0)
            status = decision.get("status", "UNKNOWN")
            tx_id = settlement.get("tx_id", "N/A")

            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Burst #{cycle:<4} | Status={status} | Root={root_idx:<3} | "
                f"Weight={weight:.3f} | TxID={tx_id}"
            )
        except urllib.error.URLError as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Server unavailable: {e.reason}")
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ Error: {e}")

        time.sleep(INTERVAL_SEC)

if __name__ == "__main__":
    main()

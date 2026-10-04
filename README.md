# Tordial-GS: Sovereign Edge Mesh & Autonomous Scientific Reasoning Engine

[![Test Suite](https://img.shields.io/badge/pytest-88%20passed-brightgreen.svg)](tests/)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Mesh Topology](https://img.shields.io/badge/topology-6--node%20failover-informational.svg)](core/mesh/)
[![LLM Bridge](https://img.shields.io/badge/reasoning-grok--4.3%20live-purple.svg)](scripts/run_grok_eval.py)

Tordial-GS is a high-performance edge compute architecture combining distributed failover mesh networking, topological E8 root dispatching, and live autonomous scientific reasoning via the xAI API.

---

## Technical Architecture

[ Edge Hardware (Termux / Linux) ]
│
├── core/mesh/
│     ├── failover_router.py      (6-node dynamic mesh with penalty decay)
│     ├── router.py               (Sovereign mesh packet routing)
│     └── ledger_settlement.py    (Cryptographic settlement & balance tracking)
│
├── core/bridge/
│     ├── xai_client.py           (xAI Grok-4.3 function calling & DAG runner)
│     └── sandboxes.py            (Sandboxed Python execution environment)
│
└── scripts/
├── run_grok_eval.py        (Scientific replication benchmark harness)
├── peer_heartbeat_emitter.py (Active keepalive monitor)
└── manifold_telemetry_bridge.py (Real-time telemetry streamer)


---

## Ground Truth Scientific Benchmarks

The framework evaluates autonomous agents against canonical, empirically grounded physics and material science invariants (`tests/fixtures/replica_benchmark.py`):

1. **`REP_PHYS_001` (Classical Mechanics):** Damped harmonic oscillation parameter estimation ($\zeta = 0.125$, $\omega_n = 4.712 \text{ rad/s}$).
2. **`REP_BIO_002` (Structural Biology):** Ramachandran dihedral angle envelope validity ($\phi, \psi$ steric boundary convergence).
3. **`REP_MAT_003` (Materials Science):** Goldschmidt perovskite crystal tolerance factor stability ($0.8 \le t \le 1.0$).

---

## Verification & Execution

### 1. Run Complete Test Suite
```bash
PYTHONPATH=. pytest -v
Current test suite: 88 passed (4.38s).
​2. Run Live Scientific Evaluation Harness
​Requires valid XAI_API_KEY:
bash
python3 scripts/run_grok_eval.py

3. Start Local Mesh Services
bash
# E8 RPC Server (Port 8080)
python3 core/mesh/server.py &

# WebSocket Telemetry Bridge (Port 50055)
python3 scripts/manifold_telemetry_bridge.py &

# Frontend Dashboard (Port 8081)
npm run dev

Theoretical & Symbolic Foundations
​Historical notes, philosophical treatises, and symbolic frameworks are maintained in docs/codex/.

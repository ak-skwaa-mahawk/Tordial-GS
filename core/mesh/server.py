import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import json
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any

from core.mesh.router import SovereignMeshRouter
from core.mesh.e8_tba_solver import E8TBASolver
from core.mesh.e8_visualizer import E8TerminalVisualizer
from core.mesh.ledger_settlement import SovereignLedgerEngine

# Shared engine singletons
router = SovereignMeshRouter(node_id="TORDIAL-EDGE-01")
tba_solver = E8TBASolver()
visualizer = E8TerminalVisualizer(solver=tba_solver)
ledger_engine = SovereignLedgerEngine()

class SovereignMeshHTTPHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/health":
            payload = {
                "status": "HEALTHY",
                "node_id": router.node_id,
                "active_roots_count": int(np.count_nonzero(router.queue_depths > 0.05)),
                "max_queue_depth": float(np.max(router.queue_depths))
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        elif path == "/metrics":
            ledger = ledger_engine.load_ledger()
            balances = ledger.get("balances", {})
            tx_count = len(ledger.get("transactions", []))
            tba_data = tba_solver.compute_steady_state_queues(T_eff=1.4)

            lines = [
                "# HELP tordial_e8_active_highways Current number of active E8 root highways with load",
                "# TYPE tordial_e8_active_highways gauge",
                f"tordial_e8_active_highways {int(np.count_nonzero(router.queue_depths > 0.05))}",
                "# HELP tordial_e8_max_queue_depth Maximum queue depth across all 240 E8 roots",
                "# TYPE tordial_e8_max_queue_depth gauge",
                f"tordial_e8_max_queue_depth {float(np.max(router.queue_depths)):.4f}",
                "# HELP tordial_tba_queue_load Thermodynamic Bethe Ansatz steady-state total queue load",
                "# TYPE tordial_tba_queue_load gauge",
                f"tordial_tba_queue_load {float(tba_data['total_queue_load']):.4f}",
                "# HELP tordial_tba_casimir_energy Vacuum ground state Casimir energy",
                "# TYPE tordial_tba_casimir_energy gauge",
                f"tordial_tba_casimir_energy {float(tba_data['ground_state_energy']):.4f}",
                "# HELP tordial_ledger_transactions_total Total recorded satoshi settlements",
                "# TYPE tordial_ledger_transactions_total counter",
                f"tordial_ledger_transactions_total {tx_count}"
            ]
            for node, bal in balances.items():
                lines.append(f'tordial_node_balance_sats{{node="{node}"}} {bal}')

            self._set_headers(200, content_type="text/plain; version=0.0.4")
            self.wfile.write(("\n".join(lines) + "\n").encode("utf-8"))

        elif path == "/api/v1/e8/highways":
            payload = {
                "total_highways": 240,
                "active_highways": int(np.count_nonzero(router.queue_depths > 0.05)),
                "queue_depths": router.queue_depths.tolist()
            }
            self._set_headers(200)
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        elif path == "/api/v1/e8/tba_spectrum":
            t_eff = float(params.get("t_eff", [1.4])[0])
            payload = tba_solver.compute_steady_state_queues(T_eff=t_eff)
            self._set_headers(200)
            self.wfile.write(json.dumps(payload).encode("utf-8"))

        elif path == "/api/v1/e8/ascii_dashboard":
            t_eff = float(params.get("t_eff", [1.4])[0])
            dashboard = visualizer.render_full_dashboard(router.queue_depths, T_eff=t_eff)
            self._set_headers(200)
            self.wfile.write(json.dumps({"dashboard": dashboard}).encode("utf-8"))

        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "NOT_FOUND"}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/v1/e8/dispatch":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len)
            req = json.loads(body.decode("utf-8")) if body else {}

            telemetry_8d = router.build_telemetry_vector(
                queue_size=float(req.get("queue_size", 4.0)),
                grad_temp=float(req.get("grad_temp", 3.0)),
                qber=float(req.get("qber", 0.01)),
                channel_loss=float(req.get("channel_loss", 0.02)),
                effective_strain=float(req.get("effective_strain", 3.5)),
                coherence=float(req.get("coherence", 0.98)),
                entropy=float(req.get("entropy", 0.2)),
                phase_drift=float(req.get("phase_drift", 0.002))
            )
            budget_sats = int(req.get("budget_sats", 500))
            record = router.route_burst(telemetry_8d, budget_sats=budget_sats)

            handoff_entry = {
                "origin": router.node_id,
                "trace": [{"node_id": router.node_id, "status": record["decision"]["status"]}]
            }
            settlement = ledger_engine.settle_burst_dispatch(handoff_entry, budget_sats=budget_sats)

            self._set_headers(200)
            self.wfile.write(json.dumps({"dispatch": record, "settlement": settlement}).encode("utf-8"))
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "NOT_FOUND"}).encode("utf-8"))

def run_server(host: str = "0.0.0.0", port: int = 8080):
    server = HTTPServer((host, port), SovereignMeshHTTPHandler)
    server.serve_forever()

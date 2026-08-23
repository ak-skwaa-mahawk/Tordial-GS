#!/usr/bin/env python3
"""Live Terminal Telemetry Dashboard:
Binds to UDP socket on port 9999 (with SO_REUSEPORT) or listens for dispatched
manifold telemetry bursts to render real-time pipeline states and metrics.
"""
import socket
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

# ANSI Formatting Codes
CLEAR_SCREEN = "\033[2J\033[H"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


class TelemetryDashboard:
    def __init__(self, host: str = "0.0.0.0", port: int = 9999, max_history: int = 10):
        self.host = host
        self.port = port
        self.max_history = max_history
        self.packet_count = 0
        self.recent_events: List[Dict[str, Any]] = []
        self.active_plans: Dict[str, Dict[str, Any]] = {}
        self.last_update = datetime.now(timezone.utc)

    def format_status(self, status: str) -> str:
        if status in ("SUCCESS", "VERIFIED", "PASSED"):
            return f"{GREEN}{BOLD}{status}{RESET}"
        elif status in ("RUNNING", "PENDING", "RETRYING"):
            return f"{YELLOW}{BOLD}{status}{RESET}"
        elif status in ("FAILED", "PRUNED", "DEADLOCKED"):
            return f"{RED}{BOLD}{status}{RESET}"
        return f"{CYAN}{status}{RESET}"

    def render(self):
        sys.stdout.write(CLEAR_SCREEN)
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        print(f"{CYAN}{BOLD}======================================================================{RESET}")
        print(f"{CYAN}{BOLD}          TORDIAL-GS :: REAL-TIME MANIFOLD TELEMETRY FEED            {RESET}")
        print(f"{CYAN}{BOLD}======================================================================{RESET}")
        print(f"{DIM} Listening on UDP {self.host}:{self.port} | Packets Captured: {self.packet_count} | {now_str}{RESET}\n")

        # Active Pipelines Table
        print(f"{BOLD}ACTIVE PIPELINES & DIRECTORS{RESET}")
        print(f"{DIM}----------------------------------------------------------------------{RESET}")
        print(f"{'PLAN ID':<22} | {'LAST NODE':<18} | {'STEP':<5} | {'REWARD':<7} | {'STATUS':<10}")
        print(f"{DIM}----------------------------------------------------------------------{RESET}")

        if not self.active_plans:
            print(f"{DIM}  Waiting for experiment dispatches...{RESET}")
        else:
            for plan_id, info in self.active_plans.items():
                node_str = info.get("node_id", "-")[:16]
                step_str = str(info.get("step", "-"))
                reward_val = info.get("reward", 0.0)
                reward_str = f"{reward_val:.2f}" if isinstance(reward_val, (int, float)) else "-"
                status_str = self.format_status(info.get("status", "RUNNING"))
                print(f"{plan_id:<22} | {node_str:<18} | {step_str:<5} | {reward_str:<7} | {status_str}")

        print(f"\n{BOLD}RECENT EVENT STREAM{RESET}")
        print(f"{DIM}----------------------------------------------------------------------{RESET}")

        if not self.recent_events:
            print(f"{DIM}  No telemetry events logged yet.{RESET}")
        else:
            for ev in reversed(self.recent_events[-self.max_history:]):
                t_str = ev.get("time", "-")
                e_type = ev.get("type", "UNKNOWN")
                payload = ev.get("payload", {})
                
                type_color = MAGENTA if "deadlock" in e_type else GREEN
                print(f"[{DIM}{t_str}{RESET}] {type_color}{BOLD}{e_type:<20}{RESET} {DIM}>>{RESET} {json.dumps(payload)}")

        print(f"{DIM}----------------------------------------------------------------------{RESET}")
        print(f"{DIM}Press Ctrl+C to exit dashboard.{RESET}")
        sys.stdout.flush()

    def process_packet(self, data_bytes: bytes):
        try:
            msg = json.loads(data_bytes.decode("utf-8"))
            self.packet_count += 1
            e_type = msg.get("type", "event")
            payload = msg.get("payload", {})
            timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")

            plan_id = payload.get("plan_id", "GLOBAL")
            if plan_id not in self.active_plans:
                self.active_plans[plan_id] = {}

            if e_type == "experiment_step":
                self.active_plans[plan_id].update({
                    "node_id": payload.get("node_id"),
                    "step": payload.get("step"),
                    "reward": payload.get("reward"),
                    "efficiency": payload.get("efficiency"),
                    "status": "RUNNING"
                })
            elif e_type == "experiment_summary":
                self.active_plans[plan_id].update({
                    "status": payload.get("status", "SUCCESS"),
                    "efficiency": payload.get("efficiency")
                })
            elif e_type == "experiment_deadlock":
                self.active_plans[plan_id].update({
                    "status": "DEADLOCKED"
                })

            self.recent_events.append({
                "time": timestamp,
                "type": e_type,
                "payload": payload
            })
            if len(self.recent_events) > 50:
                self.recent_events.pop(0)

            self.render()
        except Exception:
            pass

    def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Enable port and address sharing
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except (AttributeError, OSError):
                pass

        try:
            sock.bind((self.host, self.port))
        except OSError as exc:
            print(f"{RED}[!] Failed to bind UDP port {self.port}: {exc}{RESET}")
            sys.exit(1)

        self.render()
        try:
            while True:
                data, _ = sock.recvfrom(65535)
                self.process_packet(data)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}[*] Telemetry dashboard stopped.{RESET}")
        finally:
            sock.close()


def main():
    dashboard = TelemetryDashboard()
    dashboard.start()


if __name__ == "__main__":
    main()

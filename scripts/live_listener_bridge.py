import os
import sys
import json
import random
import asyncio
import sqlite3
import websockets
from dataclasses import dataclass

# CONSTANTS MAPPED FROM LIBCASCADE FIXED-POINT DEFINITIONS
EPSILON_GATE = 0x000418937
RUPTURE_LIMIT = 0x1000000000
CENTROID_MASK = 0x345BF60F8

@dataclass
class CascadeState:
    status: str
    boundary: str
    scale_omega: int
    flux_accumulator: int
    phase_velocity: int
    depth_k: int
    backpressure_pct: float

class ManifoldCascadeEngine:
    def __init__(self, db_path="manifold_cascade.db"):
        self.db_path = os.path.expanduser(f"~/Tordial-GS/scripts/{db_path}")
        self.state = CascadeState(
            status="FLUID",
            boundary="STABLE",
            scale_omega=0x0000000100000000,
            flux_accumulator=0,
            phase_velocity=0x00000001,
            depth_k=0,
            backpressure_pct=0.0
        )
        self.connected_clients = set()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_ledger (
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    step_index INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT,
                    boundary TEXT,
                    scale_omega TEXT,
                    flux_accumulator TEXT,
                    phase_velocity TEXT,
                    depth_k INTEGER,
                    backpressure_pct REAL
                )
            """)
            conn.commit()

    async def register_ws_client(self, websocket):
        self.connected_clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.connected_clients.remove(websocket)

    async def broadcast_telemetry(self, payload: dict):
        if self.connected_clients:
            msg = json.dumps(payload)
            await asyncio.gather(
                *[client.send(msg) for client in list(self.connected_clients)],
                return_exceptions=True
            )

    def process_runtime_flux(self, incoming_bytes: int) -> float:
        self.state.flux_accumulator += incoming_bytes

        if self.state.flux_accumulator >= RUPTURE_LIMIT:
            self.state.boundary = "RUPTURED"
            self.state.status = "FLUID"
            self.state.scale_omega >>= 2
            self.state.depth_k += 1
            self.state.phase_velocity = (self.state.phase_velocity ^ (CENTROID_MASK & 0xFF)) | 0x05
            self.state.flux_accumulator = 0
        else:
            self.state.boundary = "STABLE"
            effective_flux = (self.state.flux_accumulator * self.state.scale_omega) >> 32
            if effective_flux <= EPSILON_GATE:
                self.state.status = "COAGULATED"
            else:
                self.state.status = "FLUID"

        if self.state.status == "FLUID":
            self.state.backpressure_pct = min(0.95, 0.20 + (self.state.depth_k * 0.25))
        else:
            self.state.backpressure_pct = max(0.0, self.state.backpressure_pct - 0.15)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO telemetry_ledger 
                (status, boundary, scale_omega, flux_accumulator, phase_velocity, depth_k, backpressure_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.state.status,
                self.state.boundary,
                hex(self.state.scale_omega),
                hex(self.state.flux_accumulator),
                hex(self.state.phase_velocity),
                self.state.depth_k,
                round(self.state.backpressure_pct, 4)
            ))
            conn.commit()

        return self.state.backpressure_pct

class ThrottledUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, engine: ManifoldCascadeEngine, loop: asyncio.AbstractEventLoop):
        self.engine = engine
        self.loop = loop
        self.dropped_packets = 0
        self.accepted_packets = 0

    def datagram_received(self, data: bytes, addr):
        current_throttle = self.engine.state.backpressure_pct

        if current_throttle > 0.0 and random.random() < current_throttle:
            self.dropped_packets += 1
            return

        self.accepted_packets += 1
        flux_val = (len(data) << 16)
        backpressure = self.engine.process_runtime_flux(flux_val)

        payload = {
            "status": self.engine.state.status,
            "boundary": self.engine.state.boundary,
            "scale_omega": hex(self.engine.state.scale_omega),
            "depth_k": self.engine.state.depth_k,
            "backpressure_pct": round(backpressure, 4),
            "accepted": self.accepted_packets,
            "dropped": self.dropped_packets
        }

        self.loop.create_task(self.engine.broadcast_telemetry(payload))

        print(
            f"[{payload['status']} | {payload['boundary']}] "
            f"k={payload['depth_k']} | "
            f"Scale: {payload['scale_omega']} | "
            f"Throttle: {int(backpressure * 100)}% | "
            f"DropCount: {self.dropped_packets}",
            flush=True
        )

async def main():
    loop = asyncio.get_running_loop()
    engine = ManifoldCascadeEngine()

    ws_server = await websockets.serve(engine.register_ws_client, "127.0.0.1", 8766)
    print("[+] Loopback WebSocket Server active on ws://127.0.0.1:8766", flush=True)

    transport, _ = await loop.create_datagram_endpoint(
        lambda: ThrottledUDPProtocol(engine, loop),
        local_addr=("127.0.0.1", 9998)
    )
    print("[+] UDP Ingestion Port active on 127.0.0.1:9998 with active backpressure gating.", flush=True)

    try:
        await asyncio.Future()
    finally:
        transport.close()
        ws_server.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Listener bridge terminated gracefully.")

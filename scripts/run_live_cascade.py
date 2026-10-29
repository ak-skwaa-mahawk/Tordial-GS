import ctypes
import os
import time
import json
import asyncio
import websockets

# --- CTYPES STRUCTURE MAPPING ---
class CascadeNode(ctypes.Structure):
    _fields_ = [
        ("phase_pos", ctypes.c_uint64),
        ("scale_omega", ctypes.c_uint64),
        ("flux_j", ctypes.c_uint64),
        ("coagulated", ctypes.c_bool),
        ("bubble_collapsed", ctypes.c_bool)
    ]

so_path = os.path.expanduser("~/Tordial-GS/scripts/libcascade.so")
if not os.path.exists(so_path):
    raise FileNotFoundError(f"Shared library not found at: {so_path}")

cascade_lib = ctypes.CDLL(so_path)
cascade_lib.init_cascade.argtypes = [ctypes.POINTER(CascadeNode)]
cascade_lib.init_cascade.restype = None
cascade_lib.step_cascade_c.argtypes = [ctypes.POINTER(CascadeNode), ctypes.c_uint64]
cascade_lib.step_cascade_c.restype = None

RUPTURE_LIMIT = 0x1000000000

class LiveCascadeTracker:
    def __init__(self):
        self.node = CascadeNode()
        cascade_lib.init_cascade(ctypes.byref(self.node))
        self.last_ts = time.monotonic()
        self.accepted = 0
        self.dropped = 0
        self.clients = set()

    def ingest_packet_flux(self, packet_bytes: bytes) -> dict:
        now = time.monotonic()
        delta_ns = int((now - self.last_ts) * 1e9)
        self.last_ts = now

        payload_len = len(packet_bytes)
        drive_input = ((payload_len << 16) ^ (delta_ns & 0xFFFFF)) & 0xFFFFFFFFFFFFFFFF

        cascade_lib.step_cascade_c(ctypes.byref(self.node), ctypes.c_uint64(drive_input))

        if self.node.bubble_collapsed:
            self.dropped += 1
        else:
            self.accepted += 1

        # Calculate scalar depth k from scale_omega (shifts relative to 1<<32)
        omega = self.node.scale_omega
        depth_k = 0
        ref = 1 << 32
        while ref > omega and depth_k < 32:
            ref >>= 2
            depth_k += 1

        backpressure = min(1.0, float(self.node.flux_j) / float(RUPTURE_LIMIT))

        return {
            "status": "COAGULATED" if self.node.coagulated else "FLUID",
            "boundary": "RUPTURED" if self.node.bubble_collapsed else "STABLE",
            "phase_pos": f"0x{self.node.phase_pos:016X}",
            "scale_omega": f"0x{self.node.scale_omega:016X}",
            "depth_k": depth_k,
            "backpressure_pct": backpressure,
            "accepted": self.accepted,
            "dropped": self.dropped,
            "drive_input": f"0x{drive_input:016X}"
        }

    async def register_client(self, websocket):
        self.clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, telemetry: dict):
        if self.clients:
            msg = json.dumps(telemetry)
            await asyncio.gather(*[c.send(msg) for c in self.clients], return_exceptions=True)

tracker = LiveCascadeTracker()

class CascadeProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data, addr):
        telemetry = tracker.ingest_packet_flux(data)
        asyncio.create_task(tracker.broadcast(telemetry))

async def main():
    loop = asyncio.get_running_loop()

    # Bind UDP flux listener on 9998
    transport, _ = await loop.create_datagram_endpoint(
        CascadeProtocol,
        local_addr=("127.0.0.1", 9998)
    )
    print("[+] UDP Flux Listener bound on 127.0.0.1:9998", flush=True)

    # Bind WebSocket broadcast server on 8766
    async with websockets.serve(tracker.register_client, "127.0.0.1", 8766):
        print("[+] WebSocket Telemetry Server listening on ws://127.0.0.1:8766", flush=True)
        try:
            while True:
                await asyncio.sleep(3600)
        finally:
            transport.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Cascade tracker stopped.")

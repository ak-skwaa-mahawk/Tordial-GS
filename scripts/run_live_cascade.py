import ctypes
import os
import time
import json
import asyncio

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

class LiveCascadeTracker:
    def __init__(self):
        self.node = CascadeNode()
        cascade_lib.init_cascade(ctypes.byref(self.node))
        self.last_ts = time.monotonic()

    def ingest_packet_flux(self, packet_bytes: bytes) -> dict:
        now = time.monotonic()
        delta_ns = int((now - self.last_ts) * 1e9)
        self.last_ts = now

        payload_len = len(packet_bytes)
        drive_input = ((payload_len << 16) ^ (delta_ns & 0xFFFFF)) & 0xFFFFFFFFFFFFFFFF

        cascade_lib.step_cascade_c(ctypes.byref(self.node), ctypes.c_uint64(drive_input))

        return {
            "phase_pos": f"0x{self.node.phase_pos:016X}",
            "scale_omega": f"0x{self.node.scale_omega:016X}",
            "flux_j": f"0x{self.node.flux_j:016X}",
            "state": "COAGULATED" if self.node.coagulated else "FLUID",
            "boundary": "RUPTURED" if self.node.bubble_collapsed else "STABLE",
            "drive_input": f"0x{drive_input:016X}"
        }

class CascadeProtocol(asyncio.DatagramProtocol):
    def __init__(self, tracker):
        self.tracker = tracker

    def datagram_received(self, data, addr):
        telemetry = self.tracker.ingest_packet_flux(data)
        print(f"[{telemetry['state']} | {telemetry['boundary']}] Pos: {telemetry['phase_pos']} | Scale: {telemetry['scale_omega']} | Flux: {telemetry['drive_input']}", flush=True)

async def main():
    tracker = LiveCascadeTracker()
    loop = asyncio.get_running_loop()

    transport, _ = await loop.create_datagram_endpoint(
        lambda: CascadeProtocol(tracker),
        local_addr=("127.0.0.1", 9998)
    )

    print("[+] Live Cascade Tracker (DatagramProtocol) listening on UDP 127.0.0.1:9998...", flush=True)

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

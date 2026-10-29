import sys
import json
import asyncio
import websockets
import os

def render_gauge(pct: float, width: int = 20) -> str:
    filled = int(round(pct * width))
    empty = width - filled
    return f"[{'#' * filled}{'.' * empty}] {int(pct * 100)}%"

async def monitor():
    uri = "ws://127.0.0.1:8766"
    async with websockets.connect(uri) as ws:
        while True:
            frame = await ws.recv()
            data = json.loads(frame)
            
            os.system('clear')
            print("=========================================================")
            print("         MANIFOLD CASCADE TELEMETRY MONITOR             ")
            print("=========================================================")
            print(f" Status        : {data.get('status', 'N/A')} | {data.get('boundary', 'N/A')}")
            print(f" Scalar Depth  : k = {data.get('depth_k', 0)}")
            print(f" Scale Omega   : {data.get('scale_omega', '0x0')}")
            print("---------------------------------------------------------")
            throttle = data.get('backpressure_pct', 0.0)
            print(f" Backpressure  : {render_gauge(throttle)}")
            accepted = data.get('accepted', 0)
            dropped = data.get('dropped', 0)
            total = accepted + dropped
            drop_rate = (dropped / total) if total > 0 else 0.0
            print(f" Drop Rate     : {render_gauge(drop_rate)}")
            print(f" Total Ingest  : {total} (Accepted: {accepted} | Dropped: {dropped})")
            print("=========================================================")
            print(" Press Ctrl+C to disconnect from telemetry bus.")

if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("\n[!] Monitor disconnected.")

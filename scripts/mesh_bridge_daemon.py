#!/usr/bin/env python3
import asyncio
import json
import socket
import logging
import os
import ssl
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

WS_HOST = "127.0.0.1"
WS_PORT = 8765
UDP_PORT = 9999

UPLINK_WSS_URL = os.getenv("MESH_UPLINK_WSS_URL", "").strip()
UPLINK_TOKEN = os.getenv("MESH_UPLINK_TOKEN", "").strip()
UPLINK_VERIFY_TLS = os.getenv("MESH_UPLINK_VERIFY_TLS", "1").strip() not in ("0", "false", "False")

connected_clients = set()
outbound_queue = asyncio.Queue(maxsize=1024)

async def ws_handler(websocket):
    connected_clients.add(websocket)
    logging.info(f"🛰️  [BRIDGE]: Client connected from {websocket.remote_address}")
    try:
        async for message in websocket:
            for client in connected_clients:
                if client != websocket:
                    await client.send(message)
    except Exception:
        pass
    finally:
        connected_clients.remove(websocket)
        logging.info("🛰️  [BRIDGE]: Client disconnected.")

async def udp_listener_loop():
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.setblocking(False)
    logging.info(f"⚡ [BRIDGE]: Listening for UDP bursts on 0.0.0.0:{UDP_PORT}")

    while True:
        data, addr = await loop.sock_recvfrom(sock, 4096)
        msg = data.decode("utf-8", errors="ignore")

        # 1. Distribute to local WebSocket subscribers
        if connected_clients:
            await asyncio.gather(
                *[client.send(msg) for client in connected_clients],
                return_exceptions=True
            )

        # 2. Enqueue for outbound TLS/WSS telemetry uplink
        if UPLINK_WSS_URL:
            if outbound_queue.full():
                try:
                    outbound_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await outbound_queue.put(msg)

async def outbound_uplink_worker():
    if not UPLINK_WSS_URL:
        logging.info("🌐 [UPLINK]: MESH_UPLINK_WSS_URL not configured. Outbound relay idle.")
        while True:
            await asyncio.sleep(3600)

    logging.info(f"🌐 [UPLINK]: Configured target: {UPLINK_WSS_URL} (TLS Verify: {UPLINK_VERIFY_TLS})")
    
    ssl_context = None
    if UPLINK_WSS_URL.startswith("wss://"):
        ssl_context = ssl.create_default_context()
        if not UPLINK_VERIFY_TLS:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

    headers = {}
    if UPLINK_TOKEN:
        headers["Authorization"] = f"Bearer {UPLINK_TOKEN}"

    backoff = 1.0
    while True:
        try:
            logging.info(f"🌐 [UPLINK]: Connecting to remote endpoint {UPLINK_WSS_URL}...")
            extra_kwargs = {}
            if ssl_context:
                extra_kwargs["ssl"] = ssl_context

            # Compatibility across websockets versions
            try:
                if headers:
                    ws_ctx = websockets.connect(UPLINK_WSS_URL, additional_headers=headers, **extra_kwargs)
                else:
                    ws_ctx = websockets.connect(UPLINK_WSS_URL, **extra_kwargs)
            except TypeError:
                if headers:
                    ws_ctx = websockets.connect(UPLINK_WSS_URL, extra_headers=headers, **extra_kwargs)
                else:
                    ws_ctx = websockets.connect(UPLINK_WSS_URL, **extra_kwargs)

            async with ws_ctx as ws:
                logging.info("🚀 [UPLINK]: Telemetry stream connected and authenticated.")
                backoff = 1.0

                while True:
                    msg = await outbound_queue.get()
                    await ws.send(msg)
                    outbound_queue.task_done()
                    logging.info("📡 [UPLINK]: Forwarded certified audit frame to remote peer.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.warning(f"⚠️ [UPLINK]: Connection error ({type(e).__name__}: {e}). Retrying in {backoff:.1f}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2.0, 30.0)

async def main():
    server = await websockets.serve(ws_handler, WS_HOST, WS_PORT)
    logging.info(f"✅ [BRIDGE]: WS Broadcaster running at ws://{WS_HOST}:{WS_PORT}")
    
    await asyncio.gather(
        server.wait_closed(),
        udp_listener_loop(),
        outbound_uplink_worker()
    )

if __name__ == "__main__":
    asyncio.run(main())

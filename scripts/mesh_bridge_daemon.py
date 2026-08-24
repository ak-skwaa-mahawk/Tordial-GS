#!/usr/bin/env python3
import asyncio
import json
import socket
import logging
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

WS_HOST = "127.0.0.1"
WS_PORT = 8765
UDP_PORT = 9999

connected_clients = set()

async def ws_handler(websocket):
    connected_clients.add(websocket)
    logging.info(f"🛰️  [BRIDGE]: Client connected from {websocket.remote_address}")
    try:
        async for message in websocket:
            # Broadcast incoming client frames to all other listeners
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
        if connected_clients:
            msg = data.decode("utf-8", errors="ignore")
            # Broadcast to all active subscribers (e.g. settlement_worker)
            await asyncio.gather(
                *[client.send(msg) for client in connected_clients],
                return_exceptions=True
            )

async def main():
    server = await websockets.serve(ws_handler, WS_HOST, WS_PORT)
    logging.info(f"✅ [BRIDGE]: WS Broadcaster running at ws://{WS_HOST}:{WS_PORT}")
    await asyncio.gather(server.wait_closed(), udp_listener_loop())

if __name__ == "__main__":
    asyncio.run(main())

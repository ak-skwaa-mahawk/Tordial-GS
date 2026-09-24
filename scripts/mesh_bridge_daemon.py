#!/usr/bin/env python3
import asyncio
import json
import socket
import struct
import logging
import os
import ssl
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

WS_HOST = "127.0.0.1"
WS_PORT = 8765
UDP_PORT = 9999

SOVA_MAGIC = 0x534F5641
SOVR_FLAG_STATUTORY_DUTY      = (1 << 0)
SOVR_FLAG_CORP_DEFENSE_VALID  = (1 << 1)
SOVR_FLAG_CAN_BE_ADMINISTERED = (1 << 2)
SOVR_FLAG_ANOMALY_DETECTED    = (1 << 3)

UPLINK_WSS_URL = os.getenv("MESH_UPLINK_WSS_URL", "").strip()
UPLINK_TOKEN = os.getenv("MESH_UPLINK_TOKEN", "").strip()
UPLINK_VERIFY_TLS = os.getenv("MESH_UPLINK_VERIFY_TLS", "1").strip() not in ("0", "false", "False")

connected_clients = set()
outbound_queue = asyncio.Queue(maxsize=1024)

def decode_telemetry_payload(data: bytes) -> str:
    if len(data) >= 40:
        magic_val = struct.unpack_from("<I", data, 0)[0]
        if magic_val == SOVA_MAGIC:
            magic, status_code, flags = struct.unpack("<IHH", data[:8])
            root_hash = data[8:40].hex()
            is_anomaly = bool(flags & SOVR_FLAG_ANOMALY_DETECTED)
            payload = {
                "type": "EVALUATION_FRAME",
                "magic": f"0x{magic:08x}",
                "status_code": f"0x{status_code:04x}",
                "flags": {
                    "raw": flags,
                    "statutory_duty": bool(flags & SOVR_FLAG_STATUTORY_DUTY),
                    "corporate_defense_valid": bool(flags & SOVR_FLAG_CORP_DEFENSE_VALID),
                    "can_be_administered_away": bool(flags & SOVR_FLAG_CAN_BE_ADMINISTERED),
                    "anomaly_detected": is_anomaly
                },
                "root_hash": root_hash
            }
            if is_anomaly:
                payload["alert"] = {
                    "level": "CRITICAL",
                    "message": "In-Kernel TinyML Anomaly Classification Triggered (0x0008)",
                    "subsystem": "tinyml_runtime"
                }
            return json.dumps(payload)

    try:
        parsed = json.loads(data.decode("utf-8"))
        if isinstance(parsed, dict):
            flags_val = parsed.get("flags", 0)
            raw_flags = flags_val if isinstance(flags_val, int) else flags_val.get("raw", 0)
            if raw_flags & SOVR_FLAG_ANOMALY_DETECTED:
                parsed["alert"] = {
                    "level": "CRITICAL",
                    "message": "In-Kernel TinyML Anomaly Classification Triggered (0x0008)",
                    "subsystem": "tinyml_runtime"
                }
            return json.dumps(parsed)
    except Exception:
        pass

    return data.decode("utf-8", errors="ignore")

async def ws_handler(websocket):
    connected_clients.add(websocket)
    logging.info(f"Client connected: {websocket.remote_address}")
    try:
        async for message in websocket:
            for client in list(connected_clients):
                if client != websocket:
                    await client.send(message)
    except Exception:
        pass
    finally:
        connected_clients.remove(websocket)
        logging.info("Client disconnected.")

async def udp_listener_loop():
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_PORT))
    sock.setblocking(False)
    logging.info(f"Listening for UDP bursts on 0.0.0.0:{UDP_PORT}")

    while True:
        data, addr = await loop.sock_recvfrom(sock, 4096)
        msg = decode_telemetry_payload(data)

        if "CRITICAL" in msg:
            logging.warning(f"ANOMALY BROADCAST: {msg}")
        else:
            logging.info(f"TELEMETRY BROADCAST: {msg}")

        if connected_clients:
            await asyncio.gather(
                *[client.send(msg) for client in list(connected_clients)],
                return_exceptions=True
            )

        if UPLINK_WSS_URL:
            if outbound_queue.full():
                try:
                    outbound_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await outbound_queue.put(msg)

async def uplink_sender_loop():
    if not UPLINK_WSS_URL:
        return
    ssl_ctx = ssl.create_default_context() if UPLINK_VERIFY_TLS else ssl._create_unverified_context()
    headers = {"Authorization": f"Bearer {UPLINK_TOKEN}"} if UPLINK_TOKEN else {}

    while True:
        try:
            async with websockets.connect(UPLINK_WSS_URL, extra_headers=headers, ssl=ssl_ctx) as ws:
                while True:
                    msg = await outbound_queue.get()
                    await ws.send(msg)
                    outbound_queue.task_done()
        except Exception:
            await asyncio.sleep(5)

async def main():
    async with websockets.serve(ws_handler, WS_HOST, WS_PORT):
        logging.info(f"WS Broadcaster running at ws://{WS_HOST}:{WS_PORT}")
        await asyncio.gather(
            udp_listener_loop(),
            uplink_sender_loop()
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

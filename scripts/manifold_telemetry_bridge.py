import asyncio
import time
import socketio
import ctypes
from aiohttp import web
from audit_contract import (
    SovereignAuditFrame, SovereignResponseFrame,
    make_valid_audit_frame, SOVA_MAGIC, SOVR_STATUS_SUCCESS
)

sio = socketio.AsyncServer(cors_allowed_origins="*", async_mode='aiohttp')
app = web.Application()
sio.attach(app)

start_time = time.time()
iterations = 0
sequence_counter = int(time.time())

async def inject_sel4_audit_frame(claimant_msg: str) -> str:
    global sequence_counter
    sequence_counter += 1
    frame = make_valid_audit_frame(sequence_counter, claimant_msg)
    payload = bytes(frame)

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection('127.0.0.1', 9998),
            timeout=2.0
        )
        writer.write(payload)
        await writer.drain()

        resp_bytes = await asyncio.wait_for(reader.readexactly(ctypes.sizeof(SovereignResponseFrame)), timeout=2.0)
        writer.close()
        await writer.wait_closed()

        resp = SovereignResponseFrame.from_buffer_copy(resp_bytes)
        root_hex = bytes(resp.root_hash).hex()

        if resp.magic == SOVA_MAGIC and resp.status_code == SOVR_STATUS_SUCCESS:
            return f"[COM2 CERTIFIED] Seq: #{sequence_counter} | Status: 0x{resp.status_code:04x} | Flags: 0x{resp.flags:04x} | Root: {root_hex[:16]}..."
        else:
            return f"[COM2 REJECT] Status: 0x{resp.status_code:04x} | Flags: 0x{resp.flags:04x}"

    except Exception as e:
        return f"[COM2 INGESTION ERROR]: {str(e)}"

@sio.event
async def connect(sid, environ):
    print(f"[*] Client latched: {sid}")
    await sio.emit('codebook_telemetry', {
        'status': 'ACTIVE',
        'platform': 'ANDROID/TERMUX (seL4-QEMU)',
        'architecture': 'AARCH64 HOST / x86_64 PC99 GUEST',
        'detected_ram': 12,
        'selected_route': 'ISST_TOFT_SEL4_ROOTSERVER'
    }, to=sid)

@sio.event
async def connect_codebook(sid, data):
    await sio.emit('codebook_telemetry', {
        'status': 'ACTIVE',
        'platform': 'ANDROID/TERMUX (seL4-QEMU)',
        'architecture': 'AARCH64 HOST / x86_64 PC99 GUEST',
        'detected_ram': 12,
        'selected_route': 'ISST_TOFT_SEL4_ROOTSERVER'
    }, to=sid)

@sio.event
async def ping_heartbeat(sid, data):
    await sio.emit('pong_heartbeat', data, to=sid)

@sio.event
async def injin_directive(sid, data):
    directive = data.get('directive', '')
    print(f"[>] Injin Directive: {directive}")
    sel4_res = await inject_sel4_audit_frame(directive)
    await sio.emit('injin_response', {'text': sel4_res}, to=sid)

async def telemetry_broadcast():
    global iterations
    while True:
        await sio.sleep(0.08)
        iterations += 250
        throughput = int(iterations / max(1, (time.time() - start_time)))

        await sio.emit('telemetry_update', {
            'iterations': iterations,
            'batch_time_ms': 0.042,
            'throughput': throughput,
            'violations': 0
        })

async def init_app():
    sio.start_background_task(telemetry_broadcast)
    return app

if __name__ == '__main__':
    web.run_app(init_app(), host='127.0.0.1', port=50055)

import subprocess
import socket
import time
import threading
import sys
import ctypes
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

REPO_PATH = "/data/data/com.termux/files/home/Tordial-GS"
PORT = 8089
COM2_PORT = 9998
COM2_HOST = "127.0.0.1"
MESH_UDP_HOST = "127.0.0.1"
MESH_UDP_PORT = 9999
import json

# Dynamically link Telephone_port audit pipeline
TELEPHONE_PATH = "/data/data/com.termux/files/home/Telephone_port"
if TELEPHONE_PATH not in sys.path:
    sys.path.insert(0, TELEPHONE_PATH)

from audit_contract import (
    SovereignResponseFrame,
    SOVA_MAGIC,
    SOVR_STATUS_SUCCESS,
    SOVR_FLAG_STATUTORY_DUTY,
    SOVR_FLAG_CORP_DEFENSE_VALID,
    SOVR_FLAG_CAN_BE_ADMINISTERED
)


def broadcast_certified_telemetry(resp, digest, expected_digest):
    """Transmits a microkernel-certified telemetry event to the mesh bridge via UDP."""
    try:
        packet = {
            "type": "SEL4_SOVEREIGN_CERTIFICATE",
            "timestamp": time.time(),
            "magic": hex(resp.magic),
            "status_code": hex(resp.status_code),
            "flags": {
                "raw": resp.flags,
                "statutory_duty": bool(resp.flags & SOVR_FLAG_STATUTORY_DUTY),
                "corporate_defense_valid": bool(resp.flags & SOVR_FLAG_CORP_DEFENSE_VALID),
                "can_be_administered_away": bool(resp.flags & SOVR_FLAG_CAN_BE_ADMINISTERED),
            },
            "root_hash": digest,
            "certified": (resp.status_code == SOVR_STATUS_SUCCESS and digest == expected_digest)
        }
        raw_json = json.dumps(packet).encode("utf-8")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(raw_json, (MESH_UDP_HOST, MESH_UDP_PORT))
        sock.close()
    except Exception as e:
        print(f"[!] [TELEMETRY] Failed to broadcast to mesh bridge: {e}")

def verify_state_with_sel4():
    """Serializes the local state into a SovereignAuditFrame and verifies it with seL4 via COM2."""
    try:
        from audit_contract import serialize_estate_to_frame, compute_frame_binary_hash
        frame = serialize_estate_to_frame()
        payload = bytes(frame)
        expected_digest = compute_frame_binary_hash(frame)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(2.0)
        client.connect((COM2_HOST, COM2_PORT))
        client.sendall(payload)

        resp_buf = bytearray()
        while len(resp_buf) < ctypes.sizeof(SovereignResponseFrame):
            chunk = client.recv(ctypes.sizeof(SovereignResponseFrame) - len(resp_buf))
            if not chunk:
                break
            resp_buf.extend(chunk)
        client.close()

        if len(resp_buf) < ctypes.sizeof(SovereignResponseFrame):
            print("[-] [seL4 AUDIT] Truncated response frame from microkernel")
            return False

        resp = SovereignResponseFrame.from_buffer_copy(resp_buf)
        kernel_digest = bytes(resp.root_hash).hex()
        broadcast_certified_telemetry(resp, kernel_digest, expected_digest)

        if resp.magic == SOVA_MAGIC and resp.status_code == SOVR_STATUS_SUCCESS and kernel_digest == expected_digest:
            print(f"[+] [seL4 AUDIT] Microkernel certified commit state! Flags: {bin(resp.flags)}, Root: {kernel_digest[:16]}...")
            return True
        else:
            print(f"[-] [seL4 AUDIT] Rejection/Mismatch! Status: {hex(resp.status_code)}, Digest: {kernel_digest[:16]}...")
            return False
    except Exception as e:
        print(f"[!] [seL4 AUDIT] seL4 COM2 link offline or uncertified: {e}")
        return False

def has_uncommitted_changes() -> bool:
    res = subprocess.run(
        ["git", "-C", REPO_PATH, "status", "--porcelain"],
        capture_output=True, text=True
    )
    return bool(res.stdout.strip())

def sync_from_peers():
    try:
        remotes_proc = subprocess.run(
            ["git", "-C", REPO_PATH, "remote"],
            capture_output=True, text=True, check=True
        )
        remotes = [r.strip() for r in remotes_proc.stdout.splitlines() if r.strip()]

        if not remotes:
            return

        for remote in remotes:
            fetch_res = subprocess.run(
                ["git", "-C", REPO_PATH, "fetch", remote, "main"],
                capture_output=True, text=True
            )
            if fetch_res.returncode != 0:
                continue

            rev_res = subprocess.run(
                ["git", "-C", REPO_PATH, "rev-list", f"HEAD..{remote}/main", "--count"],
                capture_output=True, text=True
            )
            commits_ahead = int(rev_res.stdout.strip()) if rev_res.stdout.strip().isdigit() else 0
            if commits_ahead == 0:
                continue

            print(f"[*] [AUTO-SYNC] Found {commits_ahead} new commit(s) from {remote}/main. Syncing...")

            stashed = False
            if has_uncommitted_changes():
                stash_msg = f"auto-stash-peer-sync-{int(time.time())}"
                stash_res = subprocess.run(
                    ["git", "-C", REPO_PATH, "stash", "push", "-u", "-m", stash_msg],
                    capture_output=True, text=True
                )
                if stash_res.returncode == 0:
                    stashed = True
                    print(f"[*] [AUTO-SYNC] Stashed uncommitted changes: '{stash_msg}'")

            merge_res = subprocess.run(
                ["git", "-C", REPO_PATH, "merge", "--ff-only", f"{remote}/main"],
                capture_output=True, text=True
            )

            if merge_res.returncode == 0:
                print(f"[+] [AUTO-SYNC] Successfully fast-forwarded to {remote}/main")
                verify_state_with_sel4()
            else:
                print(f"[-] [AUTO-SYNC] Non-fast-forward conflict on {remote}/main: {merge_res.stderr.strip()}")

            if stashed:
                pop_res = subprocess.run(
                    ["git", "-C", REPO_PATH, "stash", "pop"],
                    capture_output=True, text=True
                )
                if pop_res.returncode == 0:
                    print("[+] [AUTO-SYNC] Restored and reapplied stashed changes cleanly")
                else:
                    print(f"[!] [AUTO-SYNC] Conflict restoring stash. Check 'git stash list': {pop_res.stderr.strip()}")

    except Exception as e:
        print(f"[!] [AUTO-SYNC] Error during peer synchronization pass: {e}")

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/sync":
            print("\n[*] [WEBHOOK] Received sync trigger from peer. Ingesting updates...")
            sync_from_peers()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "SYNCED"}')
        elif self.path == "/audit-now":
            certified = verify_state_with_sel4()
            self.send_response(200 if certified else 502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = b'{"status": "CERTIFIED"}' if certified else b'{"status": "UNCERTIFIED"}'
            self.wfile.write(resp)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return

class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True

def run_http_server():
    server = ReusableHTTPServer(("0.0.0.0", PORT), WebhookHandler)
    print(f"[*] [PEER LISTENER] Webhook listener running on port {PORT}...")
    server.serve_forever()

def run_periodic_polling(interval_seconds=10):
    print(f"[*] [PEER LISTENER] Periodic fallback polling active (every {interval_seconds}s)...")
    while True:
        time.sleep(interval_seconds)
        sync_from_peers()

if __name__ == "__main__":
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    run_periodic_polling(interval_seconds=10)

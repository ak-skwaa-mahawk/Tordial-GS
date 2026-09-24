import subprocess
import socket
import time
import threading
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

REPO_PATH = "/data/data/com.termux/files/home/Tordial-GS"
PORT = 8089
COM2_PORT = 9998
COM2_HOST = "127.0.0.1"

# Dynamically link Telephone_port audit pipeline
TELEPHONE_PATH = "/data/data/com.termux/files/home/Telephone_port"
if TELEPHONE_PATH not in sys.path:
    sys.path.insert(0, TELEPHONE_PATH)

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

        ack = bytearray()
        while len(ack) < 32:
            chunk = client.recv(32 - len(ack))
            if not chunk:
                break
            ack.extend(chunk)
        client.close()

        kernel_digest = ack.hex()
        if kernel_digest == expected_digest:
            print(f"[+] [seL4 AUDIT] Microkernel certified commit state! Root Hash: {kernel_digest[:16]}...")
            return True
        else:
            print(f"[-] [seL4 AUDIT] Hash mismatch! Expected {expected_digest[:16]}..., got {kernel_digest[:16]}...")
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

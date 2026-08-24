import subprocess
import socket
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

REPO_PATH = "/data/data/com.termux/files/home/Tordial-GS"
PORT = 8089  # Light HTTP webhook port

def sync_from_peers():
    # 1. Fetch from any configured remotes
    try:
        # Check remotes
        remotes_proc = subprocess.run(
            ["git", "-C", REPO_PATH, "remote"],
            capture_output=True, text=True, check=True
        )
        remotes = [r.strip() for r in remotes_proc.stdout.splitlines() if r.strip()]
        
        for remote in remotes:
            # Fetch silently
            fetch_res = subprocess.run(
                ["git", "-C", REPO_PATH, "fetch", remote, "main"],
                capture_output=True, text=True
            )
            if fetch_res.returncode == 0:
                # Fast-forward merge if possible
                merge_res = subprocess.run(
                    ["git", "-C", REPO_PATH, "merge", "--ff-only", f"{remote}/main"],
                    capture_output=True, text=True
                )
                if "Updating" in merge_res.stdout or "Fast-forward" in merge_res.stdout:
                    print(f"[+] [AUTO-SYNC] Fast-forwarded local branch from {remote}/main")
    except Exception as e:
        print(f"[!] [AUTO-SYNC] Error during sync pass: {e}")

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/sync":
            print("\n[*] [WEBHOOK] Received sync trigger from peer. Pulling updates...")
            sync_from_peers()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "SYNCED"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress noisy HTTP access logs
        return

def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    print(f"[*] [PEER LISTENER] Webhook listener running on port {PORT}...")
    server.serve_forever()

def run_periodic_polling(interval_seconds=60):
    print(f"[*] [PEER LISTENER] Periodic fallback polling active (every {interval_seconds}s)...")
    while True:
        time.sleep(interval_seconds)
        sync_from_peers()

if __name__ == "__main__":
    # Start HTTP webhook receiver thread
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()
    
    # Run polling loop on main thread
    run_periodic_polling(interval_seconds=60)

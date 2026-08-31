import subprocess
import socket
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

REPO_PATH = "/data/data/com.termux/files/home/Tordial-GS"
PORT = 8089

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
            # 1. Fetch remote tracking branch
            fetch_res = subprocess.run(
                ["git", "-C", REPO_PATH, "fetch", remote, "main"],
                capture_output=True, text=True
            )
            if fetch_res.returncode != 0:
                continue

            # 2. Check if remote has new commits ahead of HEAD
            rev_res = subprocess.run(
                ["git", "-C", REPO_PATH, "rev-list", f"HEAD..{remote}/main", "--count"],
                capture_output=True, text=True
            )
            commits_ahead = int(rev_res.stdout.strip()) if rev_res.stdout.strip().isdigit() else 0
            if commits_ahead == 0:
                continue

            print(f"[*] [AUTO-SYNC] Found {commits_ahead} new commit(s) from {remote}/main. Syncing...")

            stashed = False
            # 3. Stash dirty state if present
            if has_uncommitted_changes():
                stash_msg = f"auto-stash-peer-sync-{int(time.time())}"
                stash_res = subprocess.run(
                    ["git", "-C", REPO_PATH, "stash", "push", "-u", "-m", stash_msg],
                    capture_output=True, text=True
                )
                if stash_res.returncode == 0:
                    stashed = True
                    print(f"[*] [AUTO-SYNC] Stashed uncommitted changes: '{stash_msg}'")

            # 4. Fast-forward merge
            merge_res = subprocess.run(
                ["git", "-C", REPO_PATH, "merge", "--ff-only", f"{remote}/main"],
                capture_output=True, text=True
            )

            if merge_res.returncode == 0:
                print(f"[+] [AUTO-SYNC] Successfully fast-forwarded to {remote}/main")
            else:
                print(f"[-] [AUTO-SYNC] Non-fast-forward conflict on {remote}/main: {merge_res.stderr.strip()}")

            # 5. Restore stashed changes
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
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return

def run_http_server():
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
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

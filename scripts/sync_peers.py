import subprocess
import socket
import urllib.request
import concurrent.futures

def get_local_subnet():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        prefix = ".".join(ip.split(".")[:3])
        return prefix, ip
    except Exception:
        return "192.168.1", "127.0.0.1"
    finally:
        s.close()

def probe_node(ip, port=8022, timeout=0.2):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        if s.connect_ex((ip, port)) == 0:
            return ip
    except Exception:
        pass
    finally:
        s.close()
    return None

def notify_webhook(peer_ip):
    url = f"http://{peer_ip}:8089/sync"
    try:
        req = urllib.request.Request(url, data=b"", method="POST")
        urllib.request.urlopen(req, timeout=1.5)
    except Exception:
        pass

def push_to_peer(peer_ip):
    remote_url = f"ssh://{peer_ip}:8022/data/data/com.termux/files/home/Tordial-GS"
    cmd = [
        "git", "push", "--timeout=3",
        remote_url, "HEAD:main"
    ]
    try:
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        if res.returncode == 0:
            print(f"[+] [P2P SYNC] Successfully pushed to peer {peer_ip}")
            notify_webhook(peer_ip)
        else:
            print(f"[-] [P2P SYNC] Push skipped/rejected on {peer_ip}")
    except Exception as e:
        print(f"[!] [P2P SYNC] Error syncing with {peer_ip}: {e}")

def run_sync():
    prefix, self_ip = get_local_subnet()
    ips = [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" != self_ip]
    
    active_peers = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(probe_node, ips)
        active_peers = [r for r in results if r]
        
    if not active_peers:
        return

    print(f"\n[*] [P2P SYNC] Broadcasting commit to {len(active_peers)} active peer(s)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(active_peers)) as executor:
        executor.map(push_to_peer, active_peers)

if __name__ == "__main__":
    run_sync()

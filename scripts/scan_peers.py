import socket
import concurrent.futures

def get_local_subnet():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        prefix = ".".join(ip.split(".")[:3])
        return prefix, ip
    finally:
        s.close()

def probe_node(ip, port=8022, timeout=0.3):
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

def scan_network():
    prefix, self_ip = get_local_subnet()
    print(f"[*] Local IP: {self_ip} | Scanning subnet: {prefix}.1-254 on port 8022...")
    
    ips = [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" != self_ip]
    active_peers = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(probe_node, ips)
        for res in results:
            if res:
                active_peers.append(res)
                
    if active_peers:
        print("\n[+] Discovered Active Termux SSH Peers:")
        for peer in active_peers:
            print(f"    -> ssh://{peer}:8022/data/data/com.termux/files/home/Tordial-GS")
    else:
        print("\n[-] No other active Termux nodes detected on subnet.")

if __name__ == "__main__":
    scan_network()

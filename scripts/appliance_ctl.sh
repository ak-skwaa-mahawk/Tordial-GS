#!/bin/bash
set -e

SE4_DIR="$HOME/seL4-workspace/multiserver_build"
TORDIAL_DIR="$HOME/Tordial-GS"

case "$1" in
    start)
        echo "[*] Stopping any stale instances..."
        pkill -9 -f "peer_listener_daemon.py" 2>/dev/null || true
        pkill -9 -f "mesh_bridge_daemon.py" 2>/dev/null || true
        pkill -9 -f "qemu-system-x86_64" 2>/dev/null || true
        fuser -k 9998/tcp 9999/udp 8089/tcp 8765/tcp 2>/dev/null || true
        sleep 1

        echo "[*] Booting seL4 microkernel (COM1 -> ~/.sel4_com1.log, COM2 -> :9998)..."
        cd "$SE4_DIR"
        nohup "$HOME/seL4-workspace/run_sel4_com2.sh" images/libraries-3-image-x86_64-pc99 > "$HOME/.sel4_com1.log" 2>&1 &
        disown
        sleep 3

        echo "[*] Starting Mesh Bridge Daemon (UDP :9999 -> WS :8765 -> ~/.mesh_bridge.log)..."
        cd "$TORDIAL_DIR"
        nohup python3 -u scripts/mesh_bridge_daemon.py > "$HOME/.mesh_bridge.log" 2>&1 &
        disown
        sleep 1

        echo "[*] Starting Tordial-GS peer listener daemon (:8089 -> ~/.peer_listener.log)..."
        nohup python3 -u scripts/peer_listener_daemon.py > "$HOME/.peer_listener.log" 2>&1 &
        disown
        sleep 1

        echo "[+] Appliance online."
        pgrep -fl "qemu-system-x86_64|peer_listener_daemon|mesh_bridge_daemon"
        ;;

    stop)
        echo "[*] Halting sovereign evaluation appliance..."
        pkill -9 -f "peer_listener_daemon.py" 2>/dev/null || true
        pkill -9 -f "mesh_bridge_daemon.py" 2>/dev/null || true
        pkill -9 -f "qemu-system-x86_64" 2>/dev/null || true
        fuser -k 9998/tcp 9999/udp 8089/tcp 8765/tcp 2>/dev/null || true
        echo "[+] Appliance halted."
        ;;

    status)
        echo "=== ACTIVE PROCESSES ==="
        pgrep -fl "qemu-system-x86_64|peer_listener_daemon|mesh_bridge_daemon" || echo "No active processes."
        echo ""
        echo "=== RECENT KERNEL LOG ==="
        tail -n 6 "$HOME/.sel4_com1.log" 2>/dev/null | tr -d '\r' || echo "No kernel log."
        echo ""
        echo "=== RECENT DAEMON LOG ==="
        tail -n 6 "$HOME/.peer_listener.log" 2>/dev/null || echo "No daemon log."
        echo ""
        echo "=== RECENT MESH BRIDGE LOG ==="
        tail -n 6 "$HOME/.mesh_bridge.log" 2>/dev/null || echo "No bridge log."
        ;;

    audit)
        echo "[*] Requesting on-demand microkernel certification pass..."
        curl -s -X POST http://127.0.0.1:8089/audit-now
        echo ""
        ;;

    *)
        echo "Usage: $0 {start|stop|status|audit}"
        exit 1
        ;;
esac

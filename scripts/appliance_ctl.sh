#!/bin/sh
SERVICE_DIR="$HOME/service"
LOG_DIR="$HOME/.sovereign_logs"
mkdir -p "$LOG_DIR"

cleanup_stale() {
    pkill -9 -f "runsv" 2>/dev/null || true
    pkill -9 -f "runsvdir" 2>/dev/null || true
    pkill -9 -f "peer_listener_daemon.py" 2>/dev/null || true
    pkill -9 -f "mesh_bridge.py" 2>/dev/null || true
    pkill -9 -f "qemu-system-x86_64" 2>/dev/null || true
    fuser -k 9998/tcp 9999/udp 8089/tcp 8765/tcp 2>/dev/null || true
}

case "$1" in
    start)
        echo "[*] Cleaning any stale instances..."
        cleanup_stale
        sleep 1

        echo "[*] Launching runit supervisor over $SERVICE_DIR..."
        runsvdir -P "$SERVICE_DIR" > "$LOG_DIR/runsvdir.log" 2>&1 &

        # Wait up to 5 seconds for COM2 port 9998 to be listening
        retries=10
        while ! nc -z 127.0.0.1 9998 2>/dev/null && [ $retries -gt 0 ]; do
            sleep 0.5
            retries=$((retries - 1))
        done

        sleep 1
        echo "[+] Appliance online."
        pgrep -fl "qemu-system-x86_64|peer_listener_daemon|mesh_bridge|runsv"
        ;;

    stop)
        echo "[*] Halting sovereign appliance services..."
        cleanup_stale
        echo "[+] Appliance halted."
        ;;

    restart)
        $0 stop
        sleep 1
        $0 start
        ;;

    status)
        echo "=== ACTIVE PROCESSES ==="
        pgrep -fl "qemu-system-x86_64|peer_listener_daemon|mesh_bridge|runsv" || echo "No active processes."
        echo ""
        echo "=== SOCKET / PORT BINDINGS ==="
        netstat -tuln 2>/dev/null | grep -E ':(9998|9999|8089|8765)' || echo "No active listener ports."
        echo ""
        echo "=== RECENT KERNEL LOG ==="
        tail -n 6 "$HOME/.sel4_com1.log" 2>/dev/null | tr -d '\r' || echo "No kernel log."
        ;;

    logs)
        tail -n 15 "$LOG_DIR/qemu"/* "$LOG_DIR/mesh_bridge"/* "$LOG_DIR/peer_listener"/* 2>/dev/null
        ;;

    audit)
        python3 "$HOME/Tordial-GS/scripts/verify_journal_integrity.py"
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs|audit}"
        exit 1
        ;;
esac

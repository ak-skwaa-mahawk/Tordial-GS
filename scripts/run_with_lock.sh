#!/data/data/com.termux/files/usr/bin/sh

# Trap SIGINT / SIGTERM / EXIT to safely clean up locks
cleanup() {
    echo -e "\n[*] [LOCK] Execution complete. Releasing wake lock..."
    termux-wake-unlock 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[*] [LOCK] Acquiring CPU and Network Wake-Lock..."
termux-wake-lock 2>/dev/null || true

# Execute passed command
if [ $# -eq 0 ]; then
    echo "Usage: ./scripts/run_with_lock.sh <command>"
    exit 1
fi

"$@"

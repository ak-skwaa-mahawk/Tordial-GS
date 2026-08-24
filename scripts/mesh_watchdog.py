import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import time
import subprocess
import urllib.request
import urllib.error
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [WATCHDOG] %(message)s"
)
logger = logging.getLogger("watchdog")

HEALTH_URL = "http://127.0.0.1:8080/health"
CHECK_INTERVAL_SEC = 15.0
MAX_FAILURES = 3

def check_server_health(timeout: float = 3.0) -> bool:
    try:
        req = urllib.request.Request(HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False

def restart_mesh_server():
    logger.warning("🔄 Initiating emergency restart of core.mesh.server daemon...")
    
    # 1. Terminate existing instances
    subprocess.run(["pkill", "-f", "core.mesh.server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    
    # 2. Spawn fresh unbuffered daemon process
    log_file = Path.home() / "mesh_server.log"
    with open(log_file, "a") as out:
        subprocess.Popen(
            [sys.executable, "-u", "-c", "from core.mesh.server import run_server; run_server(port=8080)"],
            cwd=str(REPO_ROOT),
            stdout=out,
            stderr=out,
            start_new_session=True
        )
    logger.info("✅ Spawned fresh core.mesh.server process on port 8080")

def main():
    logger.info(f"🛡️  Starting Mesh Watchdog Daemon (interval={CHECK_INTERVAL_SEC}s, max_failures={MAX_FAILURES})")
    failures = 0

    while True:
        is_healthy = check_server_health()
        if is_healthy:
            if failures > 0:
                logger.info("✨ Mesh server status recovered to HEALTHY")
            failures = 0
        else:
            failures += 1
            logger.warning(f"⚠️ Health probe failed ({failures}/{MAX_FAILURES})")
            if failures >= MAX_FAILURES:
                restart_mesh_server()
                time.sleep(3.0)
                failures = 0

        time.sleep(CHECK_INTERVAL_SEC)

if __name__ == "__main__":
    main()

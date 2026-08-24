import subprocess
import json
import time
import os
import glob

def read_sys_file(path):
    try:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return None

def read_battery_status():
    # Method 1: Try termux-api CLI
    try:
        res = subprocess.run(["termux-battery-status"], capture_output=True, text=True, timeout=1)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            if "temperature" in data:
                return {
                    "percentage": data.get("percentage"),
                    "temperature_c": round(float(data.get("temperature", 0)), 1),
                    "status": data.get("status", "UNKNOWN"),
                    "source": "termux-api"
                }
    except Exception:
        pass

    # Method 2: Kernel /sys/class/power_supply/battery/
    batt_dir = "/sys/class/power_supply/battery"
    temp_raw = read_sys_file(os.path.join(batt_dir, "temp"))
    capacity = read_sys_file(os.path.join(batt_dir, "capacity"))
    status_str = read_sys_file(os.path.join(batt_dir, "status"))

    if temp_raw is not None or capacity is not None:
        try:
            temp_val = float(temp_raw) / 10.0 if temp_raw else None
        except ValueError:
            temp_val = None
            
        return {
            "percentage": int(capacity) if capacity and capacity.isdigit() else None,
            "temperature_c": round(temp_val, 1) if temp_val is not None else None,
            "status": status_str or "UNKNOWN",
            "source": "kernel_power_supply"
        }

    # Method 3: Generic thermal zones
    for zone in sorted(glob.glob("/sys/class/thermal/thermal_zone*")):
        type_str = read_sys_file(os.path.join(zone, "type")) or ""
        if any(keyword in type_str.lower() for keyword in ["batt", "cpu", "tsens", "soc"]):
            temp_raw = read_sys_file(os.path.join(zone, "temp"))
            if temp_raw and temp_raw.isdigit():
                val = float(temp_raw)
                val_c = val / 1000.0 if val > 1000 else val
                return {
                    "percentage": None,
                    "temperature_c": round(val_c, 1),
                    "status": f"Zone: {type_str}",
                    "source": "kernel_thermal_zone"
                }

    return None

def monitor_loop(duration_seconds=15, interval=3):
    print(f"[*] Reading telemetry for {duration_seconds}s (interval={interval}s)...")
    start = time.time()
    while time.time() - start < duration_seconds:
        data = read_battery_status()
        if data:
            temp = data.get("temperature_c")
            pct = data.get("percentage")
            st = data.get("status")
            src = data.get("source")
            warn = " [HIGH TEMP]" if (temp and temp > 42.0) else ""
            print(f"[{time.strftime('%H:%M:%S')}] Temp: {temp}°C | Level: {pct}% | Status: {st} | ({src}){warn}")
        else:
            print("[!] Thermal sensors restricted by Android SELinux policy")
        time.sleep(interval)

if __name__ == "__main__":
    monitor_loop()

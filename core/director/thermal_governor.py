import os
import glob
import time
import asyncio

class ThermalGovernor:
    def __init__(self, warn_temp=50.0, throttle_temp=55.0, pause_temp=62.0):
        self.warn_temp = warn_temp
        self.throttle_temp = throttle_temp
        self.pause_temp = pause_temp

    def get_max_temperature(self) -> float:
        # Check power supply battery temp
        batt_temp_path = "/sys/class/power_supply/battery/temp"
        if os.path.exists(batt_temp_path):
            try:
                with open(batt_temp_path, "r") as f:
                    val = float(f.read().strip())
                    return val / 10.0 if val > 100 else val
            except Exception:
                pass

        # Check all thermal zones
        temps = []
        for zone in glob.glob("/sys/class/thermal/thermal_zone*/temp"):
            try:
                with open(zone, "r") as f:
                    v = float(f.read().strip())
                    temps.append(v / 1000.0 if v > 1000 else v)
            except Exception:
                pass
        return max(temps) if temps else 40.0

    async def guard_concurrency(self, current_concurrency: int = 4) -> int:
        temp = self.get_max_temperature()
        
        if temp >= self.pause_temp:
            print(f"[!] [THERMAL CRITICAL] Core reached {temp:.1f}°C >= {self.pause_temp}°C. Pausing for 5s...")
            await asyncio.sleep(5)
            return 1
        elif temp >= self.throttle_temp:
            print(f"[*] [THERMAL THROTTLE] Core at {temp:.1f}°C. Restricting concurrency to 1 worker.")
            await asyncio.sleep(1)
            return 1
        elif temp >= self.warn_temp:
            return max(1, current_concurrency // 2)
            
        return current_concurrency

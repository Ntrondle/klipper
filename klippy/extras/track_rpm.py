#!/usr/bin/env python3
"""
track_rpm_poll.py – simple HTTP poller for Klipper/Moonraker

* Polls Moonraker /printer/objects/query?objects=spool_sensor
* Prints RPM to stdout
* Appends the same line to /tmp/printer_rpm.log
"""

import time
import requests
import json
import datetime as dt

# ─── USER SETTINGS ───────────────────────────────────────────────
PRINTER_IP   = "localhost"          # or "192.168.x.y"
OBJ_NAME     = "spool_sensor"       # must match printer.cfg section name
INTERVAL_S   = 0.2                  # poll period
LOG_PATH     = "/tmp/printer_rpm.log"
# ─────────────────────────────────────────────────────────────────

URL = f"http://{PRINTER_IP}/printer/objects/query"
PARAMS = {"objects": OBJ_NAME}

def fetch_rpm():
    try:
        r = requests.get(URL, params=PARAMS, timeout=1.0)
        r.raise_for_status()
        data = r.json()
        return data["result"]["status"][OBJ_NAME]["rpm"]
    except Exception as e:
        return None

def main():
    print(f"Polling {OBJ_NAME}.rpm every {INTERVAL_S}s … Ctrl-C to stop.")
    with open(LOG_PATH, "a", buffering=1) as flog:
        while True:
            rpm = fetch_rpm()
            ts  = dt.datetime.now().strftime("%H:%M:%S")
            if rpm is not None:
                line = f"[{ts}] RPM: {rpm:7.2f}"
            else:
                line = f"[{ts}] RPM: null"
            print(line)
            flog.write(line + "\n")
            time.sleep(INTERVAL_S)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""rpm_watch.py – lightweight CLI RPM monitor for Moonraker

   Usage:
       python3 rpm_watch.py                 # localhost, spool_sensor, 0.5 s
       python3 rpm_watch.py <ip> <obj> <dt> # custom ip, object, interval
"""
import sys, time, json, urllib.request, urllib.parse, datetime as dt

ip         = sys.argv[1] if len(sys.argv) > 1 else "localhost"
obj        = sys.argv[2] if len(sys.argv) > 2 else "spool_sensor"
interval   = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
url        = f"http://{ip}/printer/objects/query?objects={obj}"

def fetch_rpm():
    with urllib.request.urlopen(url, timeout=2) as f:
        data = json.load(f)
    return data["result"]["status"][obj]["rpm"]

print(f"Watching {obj}.rpm on {ip} every {interval}s …  Ctrl-C to exit.")
try:
    while True:
        rpm = fetch_rpm()
        ts  = dt.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {rpm if rpm is not None else 'null':>8}")
        time.sleep(interval)
except KeyboardInterrupt:
    print("\nExiting.")
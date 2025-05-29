import asyncio, websockets, json

WS = "ws://localhost/websocket"        # adjust IP if needed
OBJ = "spool_sensor"                   # name from printer.cfg

async def track():
    async with websockets.connect(WS) as ws:
        # ---- subscribe (must include jsonrpc) ----
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "printer.objects.subscribe",
            "params": { "objects": { OBJ: ["rpm"] } },
            "id": 1
        }))
        print("Subscribed; waiting for RPM...")

        while True:
            msg = json.loads(await ws.recv())
            if msg.get("method") == "notify_printer_objects":
                # params["objects"] is a LIST of [name, {fields}]
                for name, data in msg["params"]["objects"]:
                    if name == OBJ and "rpm" in data:
                        print(f"RPM: {data['rpm']:.1f}")

if __name__ == "__main__":
    asyncio.run(track())
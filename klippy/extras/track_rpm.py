import asyncio
import websockets
import json

MOONRAKER_WS = "ws://localhost/websocket"
SENSOR_NAME = "spool_sensor"

async def track_rpm():
    async with websockets.connect(MOONRAKER_WS) as ws:
        await ws.send(json.dumps({
            "method": "printer.objects.subscribe",
            "params": {
                "objects": {
                    SENSOR_NAME: ["rpm"]
                }
            },
            "id": 1
        }))
        print(f"Subscribed to {SENSOR_NAME}.rpm")

        while True:
            message = await ws.recv()
            data = json.loads(message)
            if "params" in data:
                update = data["params"].get("objects", {}).get(SENSOR_NAME, {})
                rpm = update.get("rpm")
                if rpm is not None:
                    print(f"RPM: {rpm:.1f}")

if __name__ == "__main__":
    asyncio.run(track_rpm())
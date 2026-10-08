"""Poll OPC UA and publish typed MQTT JSON messages to HiveMQ CE."""
import asyncio
import json
import os
from datetime import datetime, timezone
from asyncua import Client
import paho.mqtt.client as mqtt

TAGS = ["TemperatureC", "SpeedRPM", "TorqueNm", "ViscosityPaS",
        "MachineState", "BatchID", "BatchProgressPct",
        "GoodUnits", "RejectUnits", "IdealCycleTimeS"]

async def run():
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    opc_url = os.getenv("OPCUA_URL", "opc.tcp://localhost:4840/mixer/")
    broker = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    broker.connect(mqtt_host, 1883, 60)
    broker.loop_start()
    try:
        async with Client(url=opc_url) as client:
            idx = await client.get_namespace_index("urn:iot-simulation:mixer")
            mixer = await client.nodes.objects.get_child([f"{idx}:Mixer01"])
            nodes = {tag: await mixer.get_child([f"{idx}:{tag}"]) for tag in TAGS}
            previous_state = None
            while True:
                data = {tag: await node.read_value() for tag, node in nodes.items()}
                data["timestamp"] = datetime.now(timezone.utc).isoformat()
                data["machine_id"] = "Mixer01"
                data["quality"] = "GOOD"
                payload = json.dumps(data)
                broker.publish("factory/mixer01/telemetry", payload, qos=1)
                if data["MachineState"] != previous_state:
                    broker.publish("factory/mixer01/state", payload, qos=1)
                    previous_state = data["MachineState"]
                await asyncio.sleep(1)
    finally:
        broker.loop_stop()
        broker.disconnect()

async def main():
    while True:
        try:
            await run()
        except Exception as exc:
            print(f"Gateway connection retry: {exc}", flush=True)
            await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(main())

"""Synthetic mixer and OPC UA server. No connection to real equipment."""
import asyncio
import math
import random
from datetime import datetime, timezone
from asyncua import Server

async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/mixer/")
    server.set_server_name("IoT Simulation - Mixer 01")
    idx = await server.register_namespace("urn:iot-simulation:mixer")
    mixer = await server.nodes.objects.add_object(idx, "Mixer01")
    initial = {
        "TemperatureC": 24.0, "SpeedRPM": 0.0, "TorqueNm": 0.0,
        "ViscosityPaS": 0.0, "MachineState": "IDLE", "BatchID": "BATCH-0001",
        "BatchProgressPct": 0.0, "GoodUnits": 0, "RejectUnits": 0,
        "IdealCycleTimeS": 6.0
    }
    nodes = {}
    for key, value in initial.items():
        nodes[key] = await mixer.add_variable(idx, key, value)
        await nodes[key].set_writable()

    rng = random.Random()
    tick = 0
    good = reject = 0
    async with server:
        while True:
            # 120s synthetic batch cycle, with a 10s scheduled fault.
            phase = tick % 120
            state = ("SETUP" if phase < 12 else
                     "RUNNING" if phase < 70 else
                     "FAULT" if phase < 80 else
                     "RUNNING" if phase < 110 else "IDLE")
            running = state == "RUNNING"
            progress = max(0, min(100, (phase - 12) / 98 * 100))
            temperature = (68 + 3 * math.sin(tick / 11) + rng.gauss(0, .7)) if running else 26.0
            rpm = (950 + 35 * math.sin(tick / 7) + rng.gauss(0, 8)) if running else 0.0
            torque = (140 + rng.gauss(0, 5)) if running else 0.0
            viscosity = (2.4 + .13 * math.sin(tick / 17) + rng.gauss(0, .035)) if running else 0.0
            if running and tick % 6 == 0:
                # Model one unit per ideal 6s. Introduce occasional reject.
                if rng.random() < .06:
                    reject += 1
                else:
                    good += 1
            values = {
                "TemperatureC": round(temperature, 2),
                "SpeedRPM": round(rpm, 2),
                "TorqueNm": round(torque, 2),
                "ViscosityPaS": round(viscosity, 3),
                "MachineState": state,
                "BatchID": f"BATCH-{tick // 120 + 1:04d}",
                "BatchProgressPct": round(progress, 1),
                "GoodUnits": good,
                "RejectUnits": reject,
            }
            for key, value in values.items():
                await nodes[key].write_value(value)
            tick += 1
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

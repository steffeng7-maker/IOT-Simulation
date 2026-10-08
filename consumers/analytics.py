"""MQTT subscriber computing illustrative online SPC flags and OEE metrics."""
import json
import os
import sqlite3
import time
from datetime import datetime
import paho.mqtt.client as mqtt

DB = "/data/metrics.db"
os.makedirs("/data", exist_ok=True)

def connect_db():
    conn = sqlite3.connect(DB, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS samples(
        ts TEXT PRIMARY KEY, batch_id TEXT, state TEXT,
        temperature REAL, rpm REAL, viscosity REAL, good INTEGER,
        reject INTEGER, spc_alert INTEGER, availability REAL,
        performance REAL, quality REAL, oee REAL)""")
    conn.commit()
    return conn

conn = connect_db()
planned = running = 0
last_counts = None
good_delta = reject_delta = 0

def on_message(client, userdata, message):
    global planned, running, last_counts, good_delta, reject_delta
    try:
        d = json.loads(message.payload)
        state = d["MachineState"]
        counts = (int(d["GoodUnits"]), int(d["RejectUnits"]))
        if last_counts is not None:
            good_delta += max(0, counts[0] - last_counts[0])
            reject_delta += max(0, counts[1] - last_counts[1])
        last_counts = counts
        planned += 1
        running += (state == "RUNNING")
        availability = running / planned
        total = good_delta + reject_delta
        # Every telemetry sample approximates one second of planned time.
        performance = min(1.0, total * float(d["IdealCycleTimeS"]) / max(1, running))
        quality = good_delta / total if total else 1.0
        oee = availability * performance * quality
        temp, viscosity = float(d["TemperatureC"]), float(d["ViscosityPaS"])
        spc_alert = int(state == "RUNNING" and
                        (not 63 <= temp <= 73 or not 2.1 <= viscosity <= 2.7))
        conn.execute("""INSERT OR REPLACE INTO samples VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (d["timestamp"], d["BatchID"], state, temp,
                      float(d["SpeedRPM"]), viscosity, counts[0], counts[1],
                      spc_alert, availability, performance, quality, oee))
        # Keep rolling history for the demo.
        conn.execute("""DELETE FROM samples WHERE ts NOT IN
                     (SELECT ts FROM samples ORDER BY ts DESC LIMIT 20000)""")
        conn.commit()
    except Exception as exc:
        print(f"Analytics error: {exc}", flush=True)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
while True:
    try:
        client.connect(os.getenv("MQTT_HOST", "localhost"), 1883, 60)
        client.subscribe("factory/mixer01/telemetry", qos=1)
        client.loop_forever()
    except Exception as exc:
        print(f"MQTT reconnection: {exc}", flush=True)
        time.sleep(3)

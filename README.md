# Industrial IoT Simulation — Mixer → OPC UA → HiveMQ → SPC / OEE

End-to-end proof of concept for a simulated industrial batch mixer.

```text
Mixer simulator + OPC UA server (4840)
                 |
                 | OPC UA read
                 v
          OPC UA / MQTT bridge
                 |
                 | MQTT publish
                 v
          HiveMQ CE Broker (1883)
                 |
                 | MQTT subscribe
                 v
        SPC + OEE analytics consumer
                 |
                 | latest snapshot / history
                 v
          Streamlit dashboard (8501)
```

## Quick start

Requirements: Docker Desktop with Compose.

```bash
docker compose up --build
```

Open http://localhost:8501 for the dashboard. OPC UA is reachable at `opc.tcp://localhost:4840/mixer/` and MQTT at `localhost:1883` (development only).

The simulator runs a 120-second repeating batch cycle: idle/setup → running → occasional fault → running → completed. All readings are **synthetic**.

## Data contract

The OPC UA namespace contains `Mixer01` variables:
`TemperatureC`, `SpeedRPM`, `TorqueNm`, `ViscosityPaS`, `MachineState`, `BatchID`, `BatchProgressPct`, `GoodUnits`, `RejectUnits`, `IdealCycleTimeS`.

The bridge publishes one JSON record per second under `factory/mixer01/telemetry`, plus `factory/mixer01/state` when the machine state changes. Each message includes an ISO-8601 UTC timestamp and source quality indicator.

## KPI definitions

**SPC**: example engineering limits for temperature and viscosity are fixed demo thresholds, not statistically established control limits. A production SPC implementation needs subgroup strategy, validated control limits, and relevant process capability rules.

**OEE** = Availability × Performance × Quality. Availability = running time / planned production time; Performance = ideal production time / running time (capped at 100% in this demo); Quality = good units / total units. The simulator's production units and ideal cycle are illustrative and not validated against a real mixing process. Setup, stop and fault are counted as planned-production losses in this demo.

## Security / next steps

This demo intentionally uses plaintext local OPC UA and anonymous local MQTT for ease of setup. **Do not expose ports publicly or connect to production networks.** Add OPC UA certificates, MQTT TLS + credentials/ACLs, durable event storage and real product/batch master data before realistic deployments.

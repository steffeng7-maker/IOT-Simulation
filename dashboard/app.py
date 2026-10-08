"""Simple Streamlit frontend for latest MQTT-derived measurements."""
import os
import sqlite3
import time
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Industrial IoT | Mixer 01", layout="wide")
st.title("Industrial IoT · Mixer 01")
st.caption("Synthetic Mixer → OPC UA → HiveMQ → SPC / OEE · auto-refresh every 3 seconds")

@st.fragment(run_every="3s")
def live():
    if not os.path.exists("/data/metrics.db"):
        st.info("Waiting for analytics data...")
        return
    try:
        with sqlite3.connect("file:/data/metrics.db?mode=ro", uri=True, timeout=5) as conn:
            df = pd.read_sql_query("SELECT * FROM samples ORDER BY ts DESC LIMIT 300", conn)
    except (sqlite3.Error, pd.errors.DatabaseError):
        st.info("Waiting for telemetry database...")
        return
    if df.empty:
        st.info("Waiting for telemetry...")
        return
    latest = df.iloc[0]
    st.subheader(f"Machine State: {latest['state']}  ·  {latest['batch_id']}")
    a,b,c,d = st.columns(4)
    a.metric("Temperature", f"{latest['temperature']:.1f} °C")
    b.metric("Speed", f"{latest['rpm']:.0f} RPM")
    c.metric("Viscosity", f"{latest['viscosity']:.2f} Pa·s")
    d.metric("SPC", "ALERT" if latest["spc_alert"] else "OK")
    st.subheader("OEE breakdown")
    cols = st.columns(4)
    for col, label, field in zip(cols, ["Availability","Performance","Quality","OEE"],
                                 ["availability","performance","quality","oee"]):
        col.metric(label, f"{latest[field]*100:.1f}%")
    chart = df.iloc[::-1].set_index("ts")
    st.subheader("Process trend")
    st.line_chart(chart[["temperature"]], height=200)
    st.line_chart(chart[["viscosity"]], height=180)
    st.caption("SPC limits are illustrative engineering thresholds; OEE is a demo estimate, not production-certified.")

live()

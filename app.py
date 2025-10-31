import os
import math
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from datetime import datetime, timezone
from influxdb_client import InfluxDBClient

# ----------------------------
# Config general
# ----------------------------
st.set_page_config(page_title="Cubo IoT — Confort & Vibración", layout="wide", page_icon="📡")
TZ = "America/Bogota"

# ----------------------------
# Conexión InfluxDB (cache)
# ----------------------------
@st.cache_resource(show_spinner=False)
def get_client():
    s = st.secrets["influxdb"]
    return InfluxDBClient(url=s["url"], token=s["token"], org=s["org"])

@st.cache_data(show_spinner=False, ttl=15)
def query_flux(query: str) -> pd.DataFrame:
    q = get_client().query_api()
    frames = q.query_data_frame(query=query)
    if isinstance(frames, list):
        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True)
    else:
        df = frames
    # Normaliza tiempos y TZ
    if "_time" in df.columns:
        df["_time"] = pd.to_datetime(df["_time"], utc=True).dt.tz_convert(TZ)
    return df

@st.cache_data(show_spinner=False)
def list_devices(bucket: str, start: str = "-30d"):
    query = f'''
import "influxdata/influxdb/schema"
schema.tagValues(
  bucket: "{bucket}",
  tag: "device_id",
  predicate: (r) => r._measurement == "dht22" or r._measurement == "mpu6050",
  start: {start}
)
'''
    df = query_flux(query)
    vals = sorted(df["_value"].dropna().unique().tolist()) if "_value" in df else []
    return vals

def build_flux(bucket, measurement, field_regex, device_id, t_start, window):
    dev = f'|> filter(fn: (r) => r.device_id == "{device_id}")' if device_id else ""
    return f'''
from(bucket: "{bucket}")
  |> range(start: {t_start})
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r._field =~ /{field_regex}/)
  {dev}
  |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"])
'''

def df_wide(bucket, measurement, field_regex, device_id, t_start, window):
    return query_flux(build_flux(bucket, measurement, field_regex, device_id, t_start, window))

def last_value(df: pd.DataFrame, col: str):
    try:
        return float(df[col].dropna().iloc[-1])
    except Exception:
        return None

def compute_indicators(df_dht, df_mpu, th):
    alerts = []
    metrics = {}

    # Temperatura / Humedad
    t = last_value(df_dht, "temperature") if not df_dht.empty and "temperature" in df_dht.columns else None
    h = last_value(df_dht, "humidity") if not df_dht.empty and "humidity" in df_dht.columns else None
    if t is not None:
        if t > th["temp_high"]:
            alerts.append(("Alta temperatura", f"{t:.1f} °C > {th['temp_high']} °C"))
        elif t < th["temp_low"]:
            alerts.append(("Baja temperatura", f"{t:.1f} °C < {th['temp_low']} °C"))
    if h is not None:
        if h > th["hum_high"]:
            alerts.append(("Humedad elevada", f"{h:.1f}% > {th['hum_high']}%"))
        elif h < th["hum_low"]:
            alerts.append(("Humedad baja", f"{h:.1f}% < {th['hum_low']}%"))

    metrics["temperature"] = t
    metrics["humidity"] = h

    # Aceleración / Movimiento
    accel_mag = None
    tilt = {"pitch": None, "roll": None}
    if not df_mpu.empty:
        has_acc = all(c in df_mpu.columns for c in ["accel_x","accel_y","accel_z"])
        if has_acc:
            ax = df_mpu["accel_x"].dropna().to_numpy()
            ay = df_mpu["accel_y"].dropna().to_numpy()
            az = df_mpu["accel_z"].dropna().to_numpy()
            if ax.size and ay.size and az.size:
                accel_mag = float(math.sqrt(ax[-1]**2 + ay[-1]**2 + az[-1]**2))
                if accel_mag > th["accel_g"]:
                    alerts.append(("Vibración/movimiento", f"|a|={accel_mag:.2f} g > {th['accel_g']} g"))

                # Estimación estática de pitch/roll si no existen
                if "pitch" not in df_mpu.columns or "roll" not in df_mpu.columns:
                    pitch = math.degrees(math.atan2(ax[-1], math.sqrt(ay[-1]**2 + az[-1]**2)))
                    roll  = math.degrees(math.atan2(ay[-1], math.sqrt(ax[-1]**2 + az[-1]**2)))
                    tilt["pitch"], tilt["roll"] = pitch, roll
                else:
                    tilt["pitch"] = last_value(df_mpu, "pitch")
                    tilt["roll"]  = last_value(df_mpu, "roll")

    metrics["accel_mag"] = accel_mag
    metrics["pitch"] = tilt["pitch"]
    metrics["roll"]  = tilt["roll"]

    if metrics["pitch"] is not None and abs(metrics["pitch"]) > th["tilt_deg"]:
        alerts.append(("Inclinación anómala (pitch)", f"{metrics['pitch']:.1f}° > {th['tilt_deg']}°"))
    if metrics["roll"] is not None and abs(metrics["roll"]) > th["tilt_deg"]:
        alerts.append(("Inclinación anómala (roll)", f"{metrics['roll']:.1f}° > {th['tilt_deg']}°"))

    return metrics, alerts

# ----------------------------
# Sidebar / Controles
# ----------------------------
s = st.secrets["influxdb"]
bucket = s["bucket"]
st.sidebar.header("Filtros")
time_range = st.sidebar.selectbox("Rango de tiempo", ["-30m","-1h","-6h","-12h","-24h","-3d","-7d"], index=3)
window = st.sidebar.selectbox("Ventana", ["10s","30s","1m","5m","15m"], index=2)

devices = ["(Todos)"] + list_devices(bucket)
device_sel = st.sidebar.selectbox("Dispositivo (device_id)", devices, index=0)
device = None if device_sel == "(Todos)" else device_sel

st.sidebar.header("Umbrales")
th = {
    "temp_low": 18.0,
    "temp_high": 28.0,
    "hum_low": 30.0,
    "hum_high": 70.0,
    "accel_g": 1.20,   # Magnitud de aceleración en g
    "tilt_deg": 25.0,  # Inclinación permitida
}
th["temp_low"]  = st.sidebar.number_input("Temp. mínima (°C)", value=th["temp_low"], step=0.5)
th["temp_high"] = st.sidebar.number_input("Temp. máxima (°C)", value=th["temp_high"], step=0.5)
th["hum_low"]   = st.sidebar.number_input("Humedad mínima (%)", value=th["hum_low"], step=1.0)
th["hum_high"]  = st.sidebar.number_input("Humedad máxima (%)", value=th["hum_high"], step=1.0)
th["accel_g"]   = st.sidebar.number_input("Umbral |a| (g)", value=th["accel_g"], step=0.05, format="%.2f")
th["tilt_deg"]  = st.sidebar.number_input("Umbral inclinación (°)", value=th["tilt_deg"], step=1.0)

st.sidebar.header("Actualización")
auto = st.sidebar.checkbox("Auto-actualizar cada 15 s", value=True)
if auto:
    # Autorefresh (no bloqueante)
    st.autorefresh(interval=15000, key="refresher")

st.sidebar.caption("Zona horaria: " + TZ)

# ----------------------------
# Encabezado
# ----------------------------
st.title("📡 Cubo IoT — Confort térmico & vibración")
st.markdown("Monitoreo de **temperatura/humedad (DHT22)** y **movimiento/orientación (MPU6050)**.")

# ----------------------------
# Queries
# ----------------------------
df_dht = df_wide(bucket, "dht22", "^(temperature|humidity)$", device, time_range, window)
df_mpu = df_wide(bucket, "mpu6050", "^(accel_x|accel_y|accel_z|gyro_x|gyro_y|gyro_z|pitch|roll|yaw)$", device, time_range, window)

# ----------------------------
# Indicadores / Alertas
# ----------------------------
metrics, alerts = compute_indicators(df_dht, df_mpu, th)

# Banner de alertas
if alerts:
    for title, detail in alerts:
        st.error(f"**{title}** — {detail}")
else:
    st.success("Condiciones dentro de rangos establecidos.")

# Métricas de cabecera
col1, col2, col3, col4 = st.columns(4)
col1.metric("🌡️ Temperatura (°C)", f"{metrics['temperature']:.1f}" if metrics['temperature'] is not None else "—")
col2.metric("💧 Humedad (%)", f"{metrics['humidity']:.1f}" if metrics['humidity'] is not None else "—")
col3.metric("∥a∥ (g)", f"{metrics['accel_mag']:.2f}" if metrics['accel_mag'] is not None else "—")
tilt_txt = None
if metrics["pitch"] is not None or metrics["roll"] is not None:
    p = f"{metrics['pitch']:.0f}°" if metrics['pitch'] is not None else "—"
    r = f"{metrics['roll']:.0f}°" if metrics['roll'] is not None else "—"
    tilt_txt = f"{p} / {r}"
col4.metric("Inclinación (pitch/roll)", tilt_txt if tilt_txt else "—")

# ----------------------------
# Gráficas
# ----------------------------
tab1, tab2 = st.tabs(["Ambiente", "Movimiento"])

with tab1:
    st.subheader("Temperatura y Humedad")
    if df_dht.empty:
        st.info("Sin datos para DHT22 en el periodo seleccionado.")
    else:
        dfp = df_dht.rename(columns={"_time":"time"})
        fields = [c for c in ["temperature","humidity"] if c in dfp.columns]
        if fields:
            base = alt.Chart(dfp).mark_line().encode(
                x=alt.X("time:T", title="Tiempo"),
                tooltip=["time:T"] + fields
            )
            charts = [base.encode(y=alt.Y(f"{f}:Q", title=f)) for f in fields]
            st.altair_chart(alt.vconcat(*charts).resolve_scale(y='independent'), use_container_width=True)
        st.download_button("Descargar CSV (Ambiente)", df_dht.to_csv(index=False), "dht22.csv", "text/csv")

with tab2:
    st.subheader("Aceleraciones y Orientación")
    if df_mpu.empty:
        st.info("Sin datos para MPU6050 en el periodo seleccionado.")
    else:
        dfp = df_mpu.rename(columns={"_time":"time"})
        plot_fields = [c for c in ["accel_x","accel_y","accel_z","pitch","roll"] if c in dfp.columns]
        if plot_fields:
            base = alt.Chart(dfp).mark_line().encode(
                x=alt.X("time:T", title="Tiempo"),
                tooltip=["time:T"] + plot_fields
            )
            charts = [base.encode(y=alt.Y(f"{f}:Q", title=f)) for f in plot_fields]
            st.altair_chart(alt.vconcat(*charts).resolve_scale(y='independent'), use_container_width=True)
        st.download_button("Descargar CSV (Movimiento)", df_mpu.to_csv(index=False), "mpu6050.csv", "text/csv")

st.caption("Última actualización: " + datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"))

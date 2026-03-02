import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from utils import api_client

MOVING_WINDOW_MINUTES = 5

def create_gauge(value, title, min_val, max_val, key, color="blue"):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': color},
            'steps': [
                {'range': [min_val, max_val * 0.4], 'color': 'red' if title == "Health Score" else 'lightgreen'},
                {'range': [max_val * 0.4, max_val * 0.7], 'color': 'yellow'},
                {'range': [max_val * 0.7, max_val], 'color': 'green' if title == "Health Score" else 'red'},
            ]
        }
    ))
    fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=30))
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_{key}")

def create_single_trend_chart(df, column, title, color, key):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df[column], 
        mode='lines', 
        name=title,
        line=dict(color=color)
    ))
    
    fig.update_layout(
        title=f"{title} Trend (5-Minute Window)",
        xaxis_title="Time",
        yaxis_title=title,
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_trend_{key}")

def render_dashboard(asset_id: str):
    session_key = f"trend_data_{asset_id}"
    if session_key not in st.session_state:
        st.session_state[session_key] = pd.DataFrame(columns=['timestamp', 'avg_temperature', 'avg_pressure', 'avg_vibration'])

    last_timestamp_iso = None
    if not st.session_state[session_key].empty:
        last_timestamp = st.session_state[session_key]['timestamp'].max()
        last_timestamp_iso = last_timestamp.isoformat()
    else:
        # On first run, fetch the last 3 minutes of data to populate the chart initially
        three_minutes_ago = (datetime.now(timezone.utc) - timedelta(minutes=MOVING_WINDOW_MINUTES)).isoformat()
        last_timestamp_iso = three_minutes_ago

    # Fetch delta updates using interval_seconds=1 as required
    new_data = api_client.get_telemetry_history(asset_id, start_time=last_timestamp_iso, interval_seconds=1)

    if not new_data.empty:
        current_df = pd.concat([st.session_state[session_key], new_data], ignore_index=True)
        # Convert timestamp to datetime if it's not already
        current_df['timestamp'] = pd.to_datetime(current_df['timestamp'], utc=True)
        st.session_state[session_key] = current_df.drop_duplicates(subset=['timestamp']).sort_values(by='timestamp')

    # Enforce exactly 3-minute moving window on the cached data
    trend_df = st.session_state[session_key]
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=MOVING_WINDOW_MINUTES)
    trend_df = trend_df[trend_df['timestamp'] >= cutoff_time]
    st.session_state[session_key] = trend_df
    
    latest_telemetry = trend_df.iloc[-1].to_dict() if not trend_df.empty else None

    # Fetch latest health score from a separate endpoint to be absolutely accurate
    # and to demonstrate multi-endpoint interaction
    health_data = api_client.get_asset_health(asset_id)
    health_score = health_data.get('score', 100) if health_data else 100

    st.subheader(f"Status for {asset_id}")
    
    # 4 Gauges in one row: Health, Temp, Pressure, Vibration
    g_col1, g_col2, g_col3, g_col4 = st.columns(4)
    with g_col1:
        create_gauge(health_score, "Health Score", 0, 100, f"health_{asset_id}", color="green" if health_score > 70 else "orange" if health_score > 40 else "red")
    
    if latest_telemetry:
        with g_col2:
            create_gauge(latest_telemetry.get('avg_temperature', 0), "Temperature (°C)", 0, 120, f"temp_{asset_id}")
        with g_col3:
            create_gauge(latest_telemetry.get('avg_pressure', 0), "Pressure (bar)", 0, 15, f"press_{asset_id}")
        with g_col4:
            create_gauge(latest_telemetry.get('avg_vibration', 0), "Vibration (mm/s)", 0, 5, f"vib_{asset_id}")
    else:
        with g_col2: st.info("Waiting...")
        with g_col3: st.info("Waiting...")
        with g_col4: st.info("Waiting...")

    # Trends in separate rows
    if not trend_df.empty:
        st.write("---")
        create_single_trend_chart(trend_df, 'avg_pressure', "Pressure (bar)", "blue", f"press_trend_{asset_id}")
        create_single_trend_chart(trend_df, 'avg_temperature', "Temperature (°C)", "orange", f"temp_trend_{asset_id}")
        create_single_trend_chart(trend_df, 'avg_vibration', "Vibration (mm/s)", "purple", f"vib_trend_{asset_id}")
    else:
        st.info("No trend data available in the last 3 minutes.")


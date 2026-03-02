import os
import requests
import pandas as pd
from datetime import datetime, timezone

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

def get_base_url():
    return f"{BACKEND_URL}{API_PREFIX}"

def is_backend_available():
    """Checks if the backend API is reachable."""
    try:
        # Use a non-API endpoint like /health for a lightweight check
        response = requests.get(f"{BACKEND_URL}/health", timeout=1)
        return response.status_code == 200
    except requests.ConnectionError:
        return False

def get_assets():
    """Fetches the list of all assets."""
    try:
        response = requests.get(f"{get_base_url()}/assets")
        response.raise_for_status()
        return response.json()
    except (requests.ConnectionError, requests.HTTPError):
        return []

def get_telemetry_history(asset_id: str, start_time: str = None, interval_seconds: int = 1):
    """
    Fetches historical telemetry trend data for a specific asset.
    If 'start_time' is provided (ISO 8601 format), it fetches data since that timestamp.
    """
    params = {'interval_seconds': interval_seconds}
    if start_time:
        params['start_time'] = start_time
    
    try:
        url = f"{get_base_url()}/assets/{asset_id}/trends"
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
            return pd.DataFrame(columns=['timestamp', 'avg_temperature', 'avg_pressure', 'avg_vibration'])
        
        df = pd.DataFrame(data)
        # Ensure timestamps are parsed as timezone-aware UTC for consistent comparisons
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        # Map avg_ columns to the names expected by the dashboard if necessary, 
        # but better to update dashboard to use avg_ names.
        return df
    except (requests.ConnectionError, requests.HTTPError):
        return pd.DataFrame(columns=['timestamp', 'avg_temperature', 'avg_pressure', 'avg_vibration'])

def get_asset_health(asset_id: str):
    """Fetches the latest health score for an asset."""
    try:
        response = requests.get(f"{get_base_url()}/assets/{asset_id}/health")
        response.raise_for_status()
        return response.json()
    except (requests.ConnectionError, requests.HTTPError):
        return None

def get_alerts():
    """Fetches all alerts."""
    try:
        response = requests.get(f"{get_base_url()}/alerts")
        response.raise_for_status()
        return response.json()
    except (requests.ConnectionError, requests.HTTPError):
        return []

def acknowledge_alert(alert_id: str):
    """Acknowledges a specific alert using PATCH."""
    try:
        url = f"{get_base_url()}/alerts/{alert_id}"
        response = requests.patch(url, json={"status": "Acknowledged"})
        response.raise_for_status()
        return response.status_code == 200
    except (requests.ConnectionError, requests.HTTPError) as e:
        print(f"Failed to acknowledge alert {alert_id}: {e}")
        return False

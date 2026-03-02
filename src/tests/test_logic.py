import pytest
import requests
import time

# Assuming the FastAPI backend is running on this address
BASE_URL = "http://localhost:8000"

# --- Fixtures (for setup/teardown or shared resources) ---

@pytest.fixture(scope="module")
def api_client():
    """
    Fixture to provide a requests session for making API calls.
    Assumes the FastAPI backend is running.
    """
    try:
        # Basic check to ensure the API is reachable before starting tests
        response = requests.get(f"{BASE_URL}/api/v1/assets", timeout=5)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        pytest.fail(f"FastAPI backend not reachable at {BASE_URL}. Please ensure it's running.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to connect to FastAPI backend: {e}")
    return requests.Session()

@pytest.fixture(autouse=True)
def clear_backend_state(api_client):
    """
    Fixture to clear the backend state before each test.
    """
    try:
        api_client.post(f"{BASE_URL}/api/v1/debug/reset")
        time.sleep(0.5) # Give backend a moment to reset
    except requests.exceptions.RequestException:
        pass 
    yield

# --- Helper functions ---

def create_asset(client, asset_id, name="Test Asset", location="Test Location"):
    """Helper to create an asset."""
    payload = {"id": asset_id, "name": name, "location": location}
    response = client.post(f"{BASE_URL}/api/v1/assets", json=payload)
    response.raise_for_status()
    return response.json()

def post_telemetry(client, asset_id, timestamp, temperature, vibration, pressure):
    """Helper to post telemetry data."""
    payload = {
        "asset_id": asset_id,
        "timestamp": timestamp,
        "temperature": temperature,
        "vibration": vibration,
        "pressure": pressure,
    }
    response = client.post(f"{BASE_URL}/api/v1/telemetry", json=payload)
    response.raise_for_status()
    return response.json()

def get_asset_details(client, asset_id):
    """Helper to get asset details."""
    response = client.get(f"{BASE_URL}/api/v1/assets/{asset_id}")
    response.raise_for_status()
    return response.json()

def get_alerts(client, asset_id=None):
    """Helper to get alerts."""
    url = f"{BASE_URL}/api/v1/alerts"
    if asset_id:
        url += f"?asset_id={asset_id}"
    response = client.get(url)
    response.raise_for_status()
    return response.json()

# --- Test Cases ---

def test_api_v1_availability(api_client):
    """
    Verify /api/v1 endpoint availability by checking the /api/v1/assets endpoint.
    """
    print(f"\nTesting API availability at {BASE_URL}/api/v1/assets")
    response = api_client.get(f"{BASE_URL}/api/v1/assets")
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
    assert isinstance(response.json(), list), "Expected a list of assets"
    print("API /api/v1/assets is available and returns a list.")

def test_health_scoring_algorithm_accuracy(api_client):
    """
    Test the health scoring algorithm for accuracy.
    Optimal: P 4-8, T 30-70, V 0-0.5
    Score = 100 - (p_dev * 30) - (t_dev * 30) - (v_dev * 40)
    """
    asset_id = "asset_health_001"
    create_asset(api_client, asset_id)

    # Scenario 1: Normal operating conditions -> 100 health score
    post_telemetry(api_client, asset_id, "2023-10-27T10:00:00Z", 50.0, 0.25, 6.0)
    time.sleep(1.0)
    asset_details = get_asset_details(api_client, asset_id)
    initial_health = asset_details.get("health_score")
    print(f"\nInitial health for {asset_id} (normal conditions): {initial_health}")
    assert initial_health == 100

    # Scenario 2: Elevated conditions -> Medium health score
    # T = 71 (t_dev=1), P = 8.1 (p_dev=0.1), V = 0.5 (v_dev=0)
    # Score = 100 - (0.1*30) - (1*30) - (0*40) = 100 - 3 - 30 = 67
    post_telemetry(api_client, asset_id, "2023-10-27T10:00:01Z", 71.0, 0.5, 8.1)
    time.sleep(1.0)
    asset_details = get_asset_details(api_client, asset_id)
    elevated_health = asset_details.get("health_score")
    print(f"Elevated health for {asset_id}: {elevated_health}")
    assert elevated_health == 67.0

def test_threshold_breaches_and_alert_generation(api_client):
    """
    Simulate threshold breaches (Seal Leakage, Cavitation) and verify alert generation.
    - Seal Leakage: Pressure > 10.0 AND Temperature > 85.0
    - Cavitation: Pressure < 2.0 AND Vibration > 2.0
    """
    asset_id_leak = "asset_breach_leak_002"
    asset_id_cav = "asset_breach_cav_003"

    create_asset(api_client, asset_id_leak)
    create_asset(api_client, asset_id_cav)

    # Simulate Seal Leakage
    print(f"Simulating Seal Leakage for {asset_id_leak}...")
    post_telemetry(api_client, asset_id_leak, "2023-10-27T10:01:00Z", 86.0, 0.2, 11.0) 
    time.sleep(0.5)

    alerts_after_leak = get_alerts(api_client, asset_id=asset_id_leak)
    assert len(alerts_after_leak) >= 1
    assert any("Seal Leakage" in alert["message"] for alert in alerts_after_leak)

    # Simulate Cavitation
    print(f"Simulating Cavitation for {asset_id_cav}...")
    post_telemetry(api_client, asset_id_cav, "2023-10-27T10:01:01Z", 40.0, 2.1, 1.5)
    time.sleep(0.5)

    alerts_after_cav = get_alerts(api_client, asset_id=asset_id_cav)
    assert len(alerts_after_cav) >= 1
    assert any("Cavitation" in alert["message"] for alert in alerts_after_cav)

    # Verify no alerts for normal conditions
    asset_id_normal = "asset_no_breach_004"
    create_asset(api_client, asset_id_normal)
    print(f"Checking for no alerts for {asset_id_normal} under normal conditions...")
    post_telemetry(api_client, asset_id_normal, "2023-10-27T10:01:02Z", 50.0, 0.25, 6.0)
    time.sleep(0.5)
    alerts_normal = get_alerts(api_client, asset_id=asset_id_normal)
    assert len(alerts_normal) == 0, f"Expected no alerts for {asset_id_normal} under normal conditions, got {len(alerts_normal)}"
    print(f"No alerts generated for {asset_id_normal} under normal conditions.")


def test_ui_related_errors_duplicate_widget_ids(api_client):
    """
    Check for UI-related errors like duplicate widget IDs.
    """
    print("\nConceptual test for duplicate UI widget IDs (assuming backend provides UI config)...")

    simulated_ui_config = {
        "dashboard_widgets": [
            {"id": "gauge_temp", "type": "gauge", "label": "Temperature"},
            {"id": "gauge_pressure", "type": "gauge", "label": "Pressure"},
            {"id": "trend_vibration", "type": "chart", "label": "Vibration Trend"}
        ],
        "alert_table_columns": [
            {"id": "col_timestamp", "name": "Timestamp"},
            {"id": "col_message", "name": "Message"}
        ]
    }

    # Extract all potential widget/component IDs from the simulated configuration
    widget_ids = []
    if "dashboard_widgets" in simulated_ui_config:
        for widget in simulated_ui_config["dashboard_widgets"]:
            widget_ids.append(widget["id"])
    if "alert_table_columns" in simulated_ui_config:
        for col in simulated_ui_config["alert_table_columns"]:
            widget_ids.append(col["id"]) # Including column IDs for completeness if they are also considered 'widgets'

    print(f"Extracted widget/component IDs from simulated config: {widget_ids}")

    # Check for duplicates using a set for efficiency
    seen_ids = set()
    duplicate_ids = set()
    for item_id in widget_ids:
        if item_id in seen_ids:
            duplicate_ids.add(item_id)
        else:
            seen_ids.add(item_id)

    assert not duplicate_ids, f"Found duplicate UI widget IDs in backend configuration: {list(duplicate_ids)}"

    if not duplicate_ids:
        print("No duplicate UI widget IDs found in the simulated backend configuration.")
    else:
        print("Duplicate UI widget IDs found (this indicates a potential issue if backend provides these IDs).")

I want to build a real-time predictive maintenance application from scratch to monitor industrial assets. The system must support autonomous data generation, real-time health scoring, and automated failure detection.

### 1. Main Components
- **Time-Series Database:** PostgreSQL with the TimescaleDB extension to efficiently store and query high-frequency sensor telemetry.
- **FastAPI Backend:** A central processing engine that:
    - Exposes a RESTful API for data access and alert management.
    - Orchestrates a background live-data generator (direct-to-database, producing points every 0.5s).
    - Executes real-time data processing logic on every new telemetry point.
- **Streamlit Dashboard:** A high-frequency frontend (1s refresh rate) providing:
    - Real-time health gauges for assets.
    - Historical sensor trends (Pressure, Temperature, Vibration) displayed in separate rows with a 5-minute moving window.
    - Alert log management interface.

### 2. Core Scoring & Alerting Logic
- **Health Scoring (0-100):** Starts at 100 and applies weighted penalties for deviations from these optimal ranges:
    - **Pressure:** 4.0 - 8.0 bar (Weight: 30%)
    - **Temperature:** 30.0 - 70.0 °C (Weight: 30%)
    - **Vibration:** 0.0 - 0.5 mm/s (Weight: 40%)
- **Automated Failure Detection:**
    - **Seal Leakage:** Triggered when Pressure > 10.0 bar AND Temperature > 85.0 °C.
    - **Cavitation:** Triggered when Pressure < 2.0 bar AND Vibration > 2.0 mm/s.
    - **Low Health Score:** Triggered when the overall health score falls below 40.0.

### 3. API Infrastructure Requirements
- **Asset Discovery:** Endpoint to list all unique monitored assets.
- **Telemetry Access:** Endpoints to retrieve raw sensor readings and calculated features.
- **Alert Management:** Endpoints to fetch active alerts and update their lifecycle status (e.g., Acknowledged, Cleared)

# Real-Time Predictive Maintenance Application

This application monitors industrial assets in real-time, providing health scoring, automated failure detection, and a live dashboard for sensor telemetry.

## In a Nutshell
- **Real-time Monitoring**: High-frequency telemetry generation (0.1s) and processing.
- **Health Scoring**: Intelligent scoring (0-100) based on weighted deviations from optimal operating ranges.
- **Automated Alerts**: Immediate detection of Seal Leakage, Cavitation, and Low Health Score conditions.
- **Live Dashboard**: 1-second refresh rate with a strictly enforced 5-minute moving window for trends.
- **Production-Ready**: Uses **PostgreSQL with TimescaleDB** for efficient time-series data management.

## About the Project
Built with a robust tech stack for industrial-grade reliability:
- **Backend**: FastAPI with asynchronous background tasks and SQLAlchemy (asyncpg).
- **Frontend**: Streamlit using `st.fragment` for high-frequency updates and Plotly for real-time visualization.
- **Database**: PostgreSQL + TimescaleDB extension for high-performance telemetry storage.
- **Architecture**: Decoupled generator and processor using `asyncio.Queue` for maximum throughput.

## Getting Started

### Prerequisites
- Docker and Docker Compose

### Running the Application
1. Navigate to the `src` directory.
2. Build and start the containers:
   ```bash
   docker compose up -d --build
   ```
3. Once the containers are healthy:
   - Access the **Streamlit Dashboard** at `http://localhost:8501`
   - Access the **Interactive API Docs** at `http://localhost:8000/docs`

### Running Tests
Automated logic and integration tests can be run inside the backend container:
```bash
docker exec src-backend-1 pip install pytest requests
docker cp tests src-backend-1:/app/tests
docker exec src-backend-1 pytest tests/test_logic.py
```

## Further Details

### Scoring Logic
Health scores start at 100 and decrease based on weighted penalties:
- **Pressure (4.0 - 8.0 bar)**: 30% Weight
- **Temperature (30.0 - 70.0 °C)**: 30% Weight
- **Vibration (0.0 - 0.5 mm/s)**: 40% Weight

### Failure Detection Thresholds
- **Seal Leakage**: Pressure > 10.0 bar AND Temperature > 85.0 °C.
- **Cavitation**: Pressure < 2.0 bar AND Vibration > 2.0 mm/s.
- **Low Health Score**: Overall health score < 40.0.

### Technical Optimization
- **Path Consistency**: All internal API calls use the mandatory `/api/v1` prefix.
- **UI Performance**: Uses `st.session_state` to cache historical data and only fetches delta updates to minimize network load.
- **Real-time Responsiveness**: Background processors are tuned for low-latency with non-blocking async operations.
- **Scalability**: TimescaleDB hypertables ensure the system remains performant even as telemetry data grows.

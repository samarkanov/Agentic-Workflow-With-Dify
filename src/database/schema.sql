-- This schema is for a production TimescaleDB setup and is not used by the in-memory application.

-- Asset Information
CREATE TABLE assets (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- Raw Telemetry Data (Hypertable)
CREATE TABLE telemetry (
    time TIMESTAMPTZ NOT NULL,
    asset_id VARCHAR(255) REFERENCES assets(id),
    pressure DOUBLE PRECISION,
    temperature DOUBLE PRECISION,
    vibration DOUBLE PRECISION,
    PRIMARY KEY (time, asset_id)
);

-- Create a TimescaleDB hypertable from the telemetry table
SELECT create_hypertable('telemetry', 'time');

-- Alerts Table
CREATE TABLE alerts (
    id UUID PRIMARY KEY,
    asset_id VARCHAR(255) REFERENCES assets(id),
    timestamp TIMESTAMPTZ NOT NULL,
    severity VARCHAR(50),
    message TEXT,
    status VARCHAR(50) NOT NULL -- 'Active', 'Acknowledged'
);

-- Indexes for faster querying
CREATE INDEX ON telemetry (asset_id, time DESC);
CREATE INDEX ON alerts (asset_id, timestamp DESC);

from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import uuid

from typing import Optional, List

class Asset(BaseModel):
    id: str
    name: str
    location: Optional[str] = None
    health_score: Optional[float] = None

class TelemetryData(BaseModel):
    asset_id: str
    timestamp: datetime
    pressure: float
    temperature: float
    vibration: float

class HealthScore(BaseModel):
    asset_id: str
    timestamp: datetime
    score: float

class AlertStatus(str, Enum):
    ACTIVE = "Active"
    ACKNOWLEDGED = "Acknowledged"

class Alert(BaseModel):
    id: uuid.UUID
    asset_id: str
    timestamp: datetime
    severity: str
    message: str
    status: AlertStatus

class AlertUpdate(BaseModel):
    status: AlertStatus

class TrendDataPoint(BaseModel):
    timestamp: datetime
    avg_pressure: float
    avg_temperature: float
    avg_vibration: float

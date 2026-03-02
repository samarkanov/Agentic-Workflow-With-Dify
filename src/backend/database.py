import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, select, func, text
from datetime import datetime
import uuid

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class AssetDB(Base):
    __tablename__ = "assets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    location: Mapped[str] = mapped_column(String, nullable=True)

class TelemetryDB(Base):
    __tablename__ = "telemetry"
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String, ForeignKey("assets.id"), primary_key=True)
    pressure: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float] = mapped_column(Float)
    vibration: Mapped[float] = mapped_column(Float)

class AlertDB(Base):
    __tablename__ = "alerts"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[str] = mapped_column(String, ForeignKey("assets.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    severity: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="Active")

class HealthScoreDB(Base):
    __tablename__ = "health_scores"
    asset_id: Mapped[str] = mapped_column(String, ForeignKey("assets.id"), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    score: Mapped[float] = mapped_column(Float)

async def init_db():
    async with engine.begin() as conn:
        # Check if TimescaleDB extension exists, create if not
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))
        await conn.run_sync(Base.metadata.create_all)
        # Convert to hypertable if not already (this might fail if already a hypertable, so wrap in try)
        try:
            await conn.execute(text("SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE)"))
        except Exception:
            pass
        try:
            await conn.execute(text("SELECT create_hypertable('health_scores', 'timestamp', if_not_exists => TRUE)"))
        except Exception:
            pass

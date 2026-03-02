import asyncio
import random
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from fastapi import FastAPI, APIRouter, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, insert, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Asset, TelemetryData, HealthScore, Alert, AlertStatus, TrendDataPoint, AlertUpdate
)
from database import init_db, AsyncSessionLocal, AssetDB, TelemetryDB, AlertDB, HealthScoreDB

# --- Simulation Constants ---
P_MIN, P_MAX = 4.0, 8.0
T_MIN, T_MAX = 30.0, 70.0
V_MIN, V_MAX = 0.0, 0.5
HEALTH_SCORE_ALERT_THRESHOLD = 40.0

# --- Background Task Orchestration ---
telemetry_queue = asyncio.Queue()

async def data_generator():
    """Generates simulated telemetry data every 0.5 seconds for demo assets."""
    while True:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AssetDB).where(AssetDB.name.not_like("Test%")))
            assets = result.scalars().all()
            if not assets:
                initial_assets = [
                    AssetDB(id="asset-001", name="Turbine A"),
                    AssetDB(id="asset-002", name="Compressor B"),
                    AssetDB(id="asset-003", name="Pump C"),
                ]
                session.add_all(initial_assets)
                await session.commit()
                assets = initial_assets

        for asset in assets:
            # Only generate if it's not a test asset
            if asset.name.startswith("Test"):
                continue
                
            rand = random.random()
            if rand < 0.02: # Seal Leakage
                pressure = random.uniform(10.1, 15.0)
                temperature = random.uniform(85.1, 110.0)
                vibration = random.uniform(0.1, 0.4)
            elif rand < 0.04: # Cavitation
                pressure = random.uniform(0.5, 1.9)
                temperature = random.uniform(40.0, 60.0)
                vibration = random.uniform(2.1, 5.0)
            elif rand < 0.09: # Other deviations
                pressure = random.uniform(1.0, 12.0)
                temperature = random.uniform(10.0, 90.0)
                vibration = random.uniform(0.0, 2.0)
            else: # Normal operation
                pressure = random.uniform(P_MIN, P_MAX)
                temperature = random.uniform(T_MIN, T_MAX)
                vibration = random.uniform(V_MIN, V_MAX)

            telemetry_point = TelemetryData(
                asset_id=asset.id,
                timestamp=datetime.now(timezone.utc),
                pressure=round(pressure, 2),
                temperature=round(temperature, 2),
                vibration=round(vibration, 4),
            )
            await telemetry_queue.put(telemetry_point)
        await asyncio.sleep(0.5)

async def telemetry_processor():
    """Processes telemetry data to calculate health scores and generate alerts."""
    while True:
        try:
            telemetry: TelemetryData = await asyncio.wait_for(telemetry_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
            
        async with AsyncSessionLocal() as session:
            try:
                # 1. Store raw telemetry
                db_telemetry = TelemetryDB(
                    time=telemetry.timestamp,
                    asset_id=telemetry.asset_id,
                    pressure=telemetry.pressure,
                    temperature=telemetry.temperature,
                    vibration=telemetry.vibration
                )
                session.add(db_telemetry)

                # 2. Calculate Health Score
                p_dev = max(0, P_MIN - telemetry.pressure, telemetry.pressure - P_MAX)
                t_dev = max(0, T_MIN - telemetry.temperature, telemetry.temperature - T_MAX)
                v_dev = max(0, V_MIN - telemetry.vibration, telemetry.vibration - V_MAX)
                
                score = 100 - (p_dev * 30) - (t_dev * 30) - (v_dev * 40)
                score = max(0, min(100, score))

                health_db = HealthScoreDB(
                    asset_id=telemetry.asset_id,
                    timestamp=telemetry.timestamp,
                    score=round(score, 2)
                )
                session.add(health_db)

                # 3. Alert Detection
                alerts_to_check = []
                if telemetry.pressure > 10.0 and telemetry.temperature > 85.0:
                    alerts_to_check.append(("High", "Seal Leakage detected: High Pressure and High Temperature."))
                if telemetry.pressure < 2.0 and telemetry.vibration > 2.0:
                    alerts_to_check.append(("Critical", "Cavitation detected: Low Pressure and High Vibration."))
                if score < HEALTH_SCORE_ALERT_THRESHOLD:
                    alerts_to_check.append(("High", f"Low Health Score: {score:.2f}"))

                for severity, message in alerts_to_check:
                    # Check for active alert
                    stmt = select(AlertDB).where(
                        and_(
                            AlertDB.asset_id == telemetry.asset_id,
                            AlertDB.status == "Active",
                            AlertDB.message == message
                        )
                    )
                    res = await session.execute(stmt)
                    if not res.scalar():
                        alert = AlertDB(
                            id=uuid.uuid4(),
                            asset_id=telemetry.asset_id,
                            timestamp=telemetry.timestamp,
                            severity=severity,
                            message=message,
                            status="Active"
                        )
                        session.add(alert)
                
                await session.commit()
            except Exception as e:
                print(f"Error processing telemetry: {e}")
                await session.rollback()
            finally:
                telemetry_queue.task_done()

# --- FastAPI Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    generator_task = asyncio.create_task(data_generator())
    processor_task = asyncio.create_task(telemetry_processor())
    yield
    generator_task.cancel()
    processor_task.cancel()

app = FastAPI(title="Predictive Maintenance API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
async def health_check():
    return {"status": "ok"}

router = APIRouter(prefix="/api/v1")

@router.get("/assets", response_model=List[Asset])
async def get_assets():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AssetDB))
        assets_db = result.scalars().all()
        assets = []
        for a in assets_db:
            # Get latest health score
            h_stmt = select(HealthScoreDB).where(HealthScoreDB.asset_id == a.id).order_by(desc(HealthScoreDB.timestamp)).limit(1)
            h_res = await session.execute(h_stmt)
            h = h_res.scalar()
            assets.append(Asset(id=a.id, name=a.name, location=a.location, health_score=h.score if h else None))
        return assets

@router.post("/assets", response_model=Asset, status_code=status.HTTP_201_CREATED)
async def create_asset(asset: Asset):
    async with AsyncSessionLocal() as session:
        try:
            db_asset = AssetDB(id=asset.id, name=asset.name, location=asset.location)
            session.add(db_asset)
            await session.commit()
            return asset
        except Exception:
            await session.rollback()
            # If it already exists, just return it
            stmt = select(AssetDB).where(AssetDB.id == asset.id)
            res = await session.execute(stmt)
            db_asset = res.scalar()
            if db_asset:
                return Asset(id=db_asset.id, name=db_asset.name, location=db_asset.location)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create asset")

@router.get("/assets/{asset_id}", response_model=Asset)
async def get_asset(asset_id: str):
    async with AsyncSessionLocal() as session:
        stmt = select(AssetDB).where(AssetDB.id == asset_id)
        res = await session.execute(stmt)
        a = res.scalar()
        if not a:
            raise HTTPException(status_code=404, detail="Asset not found")
        # Get latest health score
        h_stmt = select(HealthScoreDB).where(HealthScoreDB.asset_id == a.id).order_by(desc(HealthScoreDB.timestamp)).limit(1)
        h_res = await session.execute(h_stmt)
        h = h_res.scalar()
        return Asset(id=a.id, name=a.name, location=a.location, health_score=h.score if h else None)

@router.get("/assets/{asset_id}/health", response_model=HealthScore)
async def get_asset_health(asset_id: str):
    async with AsyncSessionLocal() as session:
        stmt = select(HealthScoreDB).where(HealthScoreDB.asset_id == asset_id).order_by(desc(HealthScoreDB.timestamp)).limit(1)
        res = await session.execute(stmt)
        h = res.scalar()
        if not h:
            raise HTTPException(status_code=404, detail="No health data")
        return HealthScore(asset_id=h.asset_id, timestamp=h.timestamp, score=h.score)

@router.post("/telemetry", status_code=status.HTTP_201_CREATED)
async def post_telemetry(telemetry: TelemetryData):
    await telemetry_queue.put(telemetry)
    return {"status": "received"}

@router.get("/assets/{asset_id}/trends", response_model=List[TrendDataPoint])
async def get_asset_trends(asset_id: str, start_time: Optional[datetime] = None, interval_seconds: int = 1):
    async with AsyncSessionLocal() as session:
        stmt = select(TelemetryDB).where(TelemetryDB.asset_id == asset_id)
        if start_time:
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            stmt = stmt.where(TelemetryDB.time > start_time)
        else:
            # Default to last 5 minutes
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
            stmt = stmt.where(TelemetryDB.time >= cutoff)
        
        stmt = stmt.order_by(TelemetryDB.time)
        res = await session.execute(stmt)
        data = res.scalars().all()
        
        if not data: return []

        # Simple aggregation in memory for now, or could use TimescaleDB time_bucket
        buckets = {}
        for t in data:
            ts_bucket = datetime.fromtimestamp((t.time.timestamp() // interval_seconds) * interval_seconds, tz=timezone.utc)
            if ts_bucket not in buckets:
                buckets[ts_bucket] = {"p": [], "t": [], "v": []}
            buckets[ts_bucket]["p"].append(t.pressure)
            buckets[ts_bucket]["t"].append(t.temperature)
            buckets[ts_bucket]["v"].append(t.vibration)
        
        trends = []
        for ts, vals in sorted(buckets.items()):
            trends.append(TrendDataPoint(
                timestamp=ts,
                avg_pressure=round(sum(vals["p"])/len(vals["p"]), 2),
                avg_temperature=round(sum(vals["t"])/len(vals["t"]), 2),
                avg_vibration=round(sum(vals["v"])/len(vals["v"]), 4)
            ))
        return trends

@router.get("/alerts", response_model=List[Alert])
async def get_alerts(asset_id: Optional[str] = None):
    async with AsyncSessionLocal() as session:
        stmt = select(AlertDB)
        if asset_id:
            stmt = stmt.where(AlertDB.asset_id == asset_id)
        stmt = stmt.order_by(desc(AlertDB.timestamp))
        res = await session.execute(stmt)
        alerts_db = res.scalars().all()
        return [Alert(id=a.id, asset_id=a.asset_id, timestamp=a.timestamp, severity=a.severity, message=a.message, status=a.status) for a in alerts_db]

@router.patch("/alerts/{alert_id}", response_model=Alert)
async def acknowledge_alert(alert_id: uuid.UUID, alert_update: AlertUpdate):
    async with AsyncSessionLocal() as session:
        stmt = select(AlertDB).where(AlertDB.id == alert_id)
        res = await session.execute(stmt)
        alert = res.scalar()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert.status = alert_update.status
        await session.commit()
        return Alert(id=alert.id, asset_id=alert.asset_id, timestamp=alert.timestamp, severity=alert.severity, message=alert.message, status=alert.status)

@router.post("/debug/reset")
async def debug_reset():
    from sqlalchemy import delete
    async with AsyncSessionLocal() as session:
        await session.execute(delete(AlertDB))
        await session.execute(delete(HealthScoreDB))
        await session.execute(delete(TelemetryDB))
        # Keep assets for now or delete them too
        await session.execute(delete(AssetDB))
        await session.commit()
    return {"status": "reset"}

app.include_router(router)

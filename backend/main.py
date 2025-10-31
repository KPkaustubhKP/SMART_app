import os
import random
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from contextlib import asynccontextmanager
import uvicorn
import aiosqlite
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DATABASE_PATH", "agriculture_monitor.db")
db_dir = Path(DB_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

# ==================== DUMMY DATA GENERATOR ====================

class DummyDataManager:
    """Generates realistic sensor values that evolve over time"""
    
    def __init__(self):
        self.startup_time = datetime.utcnow()
        self.initialization_delay = 10  # 10 seconds before showing data
        self.last_values = {
            "soil_moisture": 0.0,
            "soil_temperature": 0.0,
            "humidity": 0.0,
            "light_intensity": 0.0,
            "soil_ph": 0.0,
            "nitrogen": 0,
            "phosphorus": 0,
            "potassium": 0,
        }
        self.realistic_values = {
            "soil_moisture": 35.5,
            "soil_temperature": 26.0,
            "humidity": 65.0,
            "light_intensity": 70.0,
            "soil_ph": 6.8,
            "nitrogen": 128,
            "phosphorus": 52,
            "potassium": 180,
        }
    
    def get_dummy_data(self):
        """Get realistic dummy data with smooth transitions"""
        seconds_elapsed = (datetime.utcnow() - self.startup_time).total_seconds()
        
        # First 10 seconds: show empty/blank values
        if seconds_elapsed < self.initialization_delay:
            logger.info(f"⏳ Initialization delay: {self.initialization_delay - int(seconds_elapsed)}s remaining")
            return {
                "soil_moisture": 0.0,
                "soil_temperature": 0.0,
                "humidity": 0.0,
                "light_intensity": 0.0,
                "soil_ph": 0.0,
                "nitrogen": 0,
                "phosphorus": 0,
                "potassium": 0,
                "status": "initializing"
            }
        
        # After 10 seconds: gradually transition to realistic values with small variations
        progress = min((seconds_elapsed - self.initialization_delay) / 30.0, 1.0)  # 30s transition
        
        # Add realistic variations
        soil_moisture = self.realistic_values["soil_moisture"] + random.uniform(-2.5, 2.5)
        soil_temperature = self.realistic_values["soil_temperature"] + random.uniform(-0.5, 0.8)
        humidity = self.realistic_values["humidity"] + random.uniform(-3, 3)
        light_intensity = self.realistic_values["light_intensity"] + random.uniform(-5, 5)
        soil_ph = self.realistic_values["soil_ph"] + random.uniform(-0.2, 0.2)
        nitrogen = int(self.realistic_values["nitrogen"] + random.uniform(-10, 10))
        phosphorus = int(self.realistic_values["phosphorus"] + random.uniform(-5, 5))
        potassium = int(self.realistic_values["potassium"] + random.uniform(-15, 15))
        
        # Clamp values to realistic ranges
        soil_moisture = max(0, min(100, soil_moisture))
        soil_temperature = max(15, min(40, soil_temperature))
        humidity = max(0, min(100, humidity))
        light_intensity = max(0, min(100, light_intensity))
        soil_ph = max(3, min(9, soil_ph))
        nitrogen = max(0, nitrogen)
        phosphorus = max(0, phosphorus)
        potassium = max(0, potassium)
        
        return {
            "soil_moisture": round(soil_moisture, 2),
            "soil_temperature": round(soil_temperature, 2),
            "humidity": round(humidity, 2),
            "light_intensity": round(light_intensity, 2),
            "soil_ph": round(soil_ph, 2),
            "nitrogen": nitrogen,
            "phosphorus": phosphorus,
            "potassium": potassium,
            "status": "initialized" if progress >= 1.0 else "transitioning"
        }

dummy_manager = DummyDataManager()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                soil_moisture REAL,
                soil_temperature REAL,
                humidity REAL,
                light_intensity REAL,
                soil_ph REAL,
                nitrogen INTEGER,
                phosphorus INTEGER,
                potassium INTEGER,
                is_dummy INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# ==================== PYDANTIC MODELS ====================

class NPKValues(BaseModel):
    nitrogen: Optional[int] = Field(None, ge=0)
    phosphorus: Optional[int] = Field(None, ge=0)
    potassium: Optional[int] = Field(None, ge=0)
    
    class Config:
        json_schema_extra = {
            "example": {"nitrogen": 125, "phosphorus": 48, "potassium": 182}
        }

class PicoSensorData(BaseModel):
    """Accepts data from Pico - all fields optional"""
    device_id: str = Field(...)
    timestamp: int = Field(...)
    soil_moisture: Optional[float] = Field(None, ge=0, le=100)
    soil_temperature: Optional[float] = Field(None)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    light_intensity: Optional[float] = Field(None, ge=0, le=100)
    soil_ph: Optional[float] = Field(None, ge=0, le=14)
    npk: Optional[NPKValues] = Field(None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "PICO_NPK_001",
                "timestamp": 1730317200,
                "soil_moisture": 35.5,
                "soil_temperature": 26.0,
                "humidity": 65.0,
                "light_intensity": 70.0,
                "soil_ph": 6.8,
                "npk": {"nitrogen": 128, "phosphorus": 52, "potassium": 180}
            }
        }

# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting application...")
    await init_db()
    logger.info("✅ Database initialized")
    logger.info("⏳ Dummy data will show after 10 second initialization delay")
    yield
    logger.info("🛑 Shutting down...")

app = FastAPI(
    title="NPK Sensor API with Demo Mode",
    description="API for Pico W NPK sensor data - shows realistic dummy data when disconnected",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== API ENDPOINTS ====================

@app.get("/health")
async def health_check():
    dummy_data = dummy_manager.get_dummy_data()
    return {
        "status": "ok",
        "message": "NPK Sensor API is running with demo mode",
        "timestamp": datetime.utcnow().isoformat(),
        "demo_status": dummy_data["status"]
    }

@app.post("/api/sensors/data")
async def receive_sensor_data(data: PicoSensorData):
    """Receive REAL sensor data from Pico - takes priority over dummy data"""
    try:
        logger.info(f"📡 REAL DATA from {data.device_id} | Temp: {data.soil_temperature}°C | Moisture: {data.soil_moisture}%")
        
        nitrogen = data.npk.nitrogen if data.npk else None
        phosphorus = data.npk.phosphorus if data.npk else None
        potassium = data.npk.potassium if data.npk else None
        
        # Mark as real data (not dummy)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO sensor_data
                (device_id, timestamp, soil_moisture, soil_temperature, humidity,
                 light_intensity, soil_ph, nitrogen, phosphorus, potassium, is_dummy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (
                    data.device_id, data.timestamp, data.soil_moisture,
                    data.soil_temperature, data.humidity, data.light_intensity,
                    data.soil_ph, nitrogen, phosphorus, potassium
                )
            )
            await db.commit()
        
        logger.info(f"✅ REAL data stored successfully - dummy data mode DISABLED")
        
        return {
            "status": "success",
            "message": "Real sensor data received and stored",
            "device_id": data.device_id,
            "timestamp": data.timestamp,
            "data_type": "real"
        }
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/sensors/current")
async def get_current_data(device_id: Optional[str] = None):
    """Get latest sensor data - shows real data if available, otherwise dummy data"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            if device_id:
                cursor = await db.execute(
                    "SELECT * FROM sensor_data WHERE device_id = ? ORDER BY timestamp DESC LIMIT 1",
                    (device_id,)
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 10"
                )
            
            rows = await cursor.fetchall()
            
            data_list = []
            for row in rows:
                data_list.append({
                    "id": row["id"],
                    "device_id": row["device_id"],
                    "timestamp": row["timestamp"],
                    "soil_moisture": row["soil_moisture"],
                    "soil_temperature": row["soil_temperature"],
                    "humidity": row["humidity"],
                    "light_intensity": row["light_intensity"],
                    "soil_ph": row["soil_ph"],
                    "npk": {
                        "nitrogen": row["nitrogen"],
                        "phosphorus": row["phosphorus"],
                        "potassium": row["potassium"]
                    },
                    "data_type": "real" if not row["is_dummy"] else "dummy",
                    "created_at": row["created_at"]
                })
            
            # If no real data, generate and show dummy data
            if not data_list:
                logger.info("📊 No real data found - returning realistic dummy data")
                dummy_data = dummy_manager.get_dummy_data()
                
                # Store dummy data in DB if not initializing
                if dummy_data["status"] != "initializing":
                    async with aiosqlite.connect(DB_PATH) as db2:
                        await db2.execute(
                            """INSERT INTO sensor_data
                            (device_id, timestamp, soil_moisture, soil_temperature, humidity,
                             light_intensity, soil_ph, nitrogen, phosphorus, potassium, is_dummy)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                            (
                                "DEMO_DEVICE",
                                int(datetime.utcnow().timestamp()),
                                dummy_data["soil_moisture"],
                                dummy_data["soil_temperature"],
                                dummy_data["humidity"],
                                dummy_data["light_intensity"],
                                dummy_data["soil_ph"],
                                dummy_data["nitrogen"],
                                dummy_data["phosphorus"],
                                dummy_data["potassium"]
                            )
                        )
                        await db2.commit()
                
                data_list = [{
                    "id": 0,
                    "device_id": "DEMO_DEVICE",
                    "timestamp": int(datetime.utcnow().timestamp()),
                    "soil_moisture": dummy_data["soil_moisture"],
                    "soil_temperature": dummy_data["soil_temperature"],
                    "humidity": dummy_data["humidity"],
                    "light_intensity": dummy_data["light_intensity"],
                    "soil_ph": dummy_data["soil_ph"],
                    "npk": {
                        "nitrogen": dummy_data["nitrogen"],
                        "phosphorus": dummy_data["phosphorus"],
                        "potassium": dummy_data["potassium"]
                    },
                    "data_type": "dummy",
                    "demo_status": dummy_data["status"],
                    "created_at": datetime.utcnow().isoformat()
                }]
            
            return {"status": "success", "count": len(data_list), "data": data_list}
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/sensors/history")
async def get_history(device_id: str, limit: int = 100):
    """Get historical data for a device"""
    try:
        if limit > 1000:
            limit = 1000
        
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            cursor = await db.execute(
                "SELECT * FROM sensor_data WHERE device_id = ? ORDER BY timestamp DESC LIMIT ?",
                (device_id, limit)
            )
            
            rows = await cursor.fetchall()
            
            data_list = []
            for row in rows:
                data_list.append({
                    "id": row["id"],
                    "device_id": row["device_id"],
                    "timestamp": row["timestamp"],
                    "soil_moisture": row["soil_moisture"],
                    "soil_temperature": row["soil_temperature"],
                    "humidity": row["humidity"],
                    "light_intensity": row["light_intensity"],
                    "soil_ph": row["soil_ph"],
                    "npk": {
                        "nitrogen": row["nitrogen"],
                        "phosphorus": row["phosphorus"],
                        "potassium": row["potassium"]
                    },
                    "data_type": "real" if not row["is_dummy"] else "dummy",
                    "created_at": row["created_at"]
                })
            
            return {"status": "success", "device_id": device_id, "count": len(data_list), "data": data_list}
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/devices")
async def get_devices():
    """Get all devices"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT DISTINCT device_id, MAX(timestamp) as last_timestamp FROM sensor_data GROUP BY device_id"
            )
            rows = await cursor.fetchall()
            
            devices = []
            for row in rows:
                devices.append({"device_id": row[0], "last_timestamp": row[1]})
            
            return {"status": "success", "count": len(devices), "devices": devices}
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Starting server on 0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

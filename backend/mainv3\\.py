import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from contextlib import asynccontextmanager
import uvicorn
import aiosqlite
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DATABASE_PATH", "agriculture_monitor.db")
db_dir = Path(DB_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

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
    """✅ FIXED: All fields optional except device_id and timestamp"""
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
                "soil_moisture": 45.2,
                "soil_temperature": 26.7,
                "humidity": 0.0,
                "light_intensity": 0.0,
                "soil_ph": 3.0,
                "npk": {"nitrogen": 0, "phosphorus": 0, "potassium": 0}
            }
        }

# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="NPK Sensor API",
    description="API for Pico W NPK sensor data",
    version="1.0.0",
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
    return {
        "status": "ok",
        "message": "NPK Sensor API is running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/sensors/data")
async def receive_sensor_data(data: PicoSensorData):
    """✅ Receive sensor data from Pico - all fields optional"""
    try:
        logger.info(f"📊 Received: {data.device_id} | Temp: {data.soil_temperature}°C | Moisture: {data.soil_moisture}%")
        
        nitrogen = data.npk.nitrogen if data.npk else None
        phosphorus = data.npk.phosphorus if data.npk else None
        potassium = data.npk.potassium if data.npk else None
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """INSERT INTO sensor_data 
                (device_id, timestamp, soil_moisture, soil_temperature, humidity, 
                 light_intensity, soil_ph, nitrogen, phosphorus, potassium)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.device_id, data.timestamp, data.soil_moisture,
                    data.soil_temperature, data.humidity, data.light_intensity,
                    data.soil_ph, nitrogen, phosphorus, potassium
                )
            )
            await db.commit()
        
        logger.info(f"✅ Data stored successfully")
        
        return {
            "status": "success",
            "message": "Data received and stored",
            "device_id": data.device_id,
            "timestamp": data.timestamp
        }
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/sensors/current")
async def get_current_data(device_id: Optional[str] = None):
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
                    "created_at": row["created_at"]
                })
            
            return {"status": "success", "count": len(data_list), "data": data_list}
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/sensors/history")
async def get_history(device_id: str, limit: int = 100):
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
                    "created_at": row["created_at"]
                })
            
            return {"status": "success", "device_id": device_id, "count": len(data_list), "data": data_list}
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/devices")
async def get_devices():
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

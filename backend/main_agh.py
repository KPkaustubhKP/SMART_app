import sys
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

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
DB_PATH = os.getenv("DATABASE_PATH", "agriculture_monitor.db")
db_dir = Path(DB_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)

async def init_db():
    """Initialize database"""
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
    """NPK sensor values - exactly as Pico sends them"""
    nitrogen: Optional[int] = Field(None, ge=0, description="Nitrogen in mg/kg")
    phosphorus: Optional[int] = Field(None, ge=0, description="Phosphorus in mg/kg")
    potassium: Optional[int] = Field(None, ge=0, description="Potassium in mg/kg")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nitrogen": 125,
                "phosphorus": 48,
                "potassium": 182
            }
        }

class PicoSensorData(BaseModel):
    """
    Exact format that Pico W sends
    Matches the JSON from main_WORKING.c
    """
    device_id: str = Field(..., description="Device ID e.g. PICO_NPK_001")
    timestamp: int = Field(..., description="Unix timestamp")
    soil_moisture: Optional[float] = Field(None, ge=0, le=100, description="Soil moisture %")
    soil_temperature: Optional[float] = Field(None, description="Temperature in °C")
    humidity: Optional[float] = Field(None, ge=0, le=100, description="Humidity %")
    light_intensity: Optional[float] = Field(None, ge=0, le=100, description="Light intensity %")
    soil_ph: Optional[float] = Field(None, ge=0, le=14, description="Soil pH")
    npk: Optional[NPKValues] = Field(None, description="NPK sensor values")
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "PICO_NPK_001",
                "timestamp": 1730317507,
                "soil_moisture": 45.2,
                "soil_temperature": 28.6,
                "humidity": 0.0,
                "light_intensity": 0.0,
                "soil_ph": 6.8,
                "npk": {
                    "nitrogen": 125,
                    "phosphorus": 48,
                    "potassium": 182
                }
            }
        }

# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown"""
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

# Enable CORS
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
    """Health check"""
    return {
        "status": "ok",
        "message": "NPK Sensor API is running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/sensors/data")
async def receive_sensor_data(data: PicoSensorData):
    """
    Receive sensor data from Pico W
    
    Accepts JSON exactly as Pico sends it:
    {
        "device_id": "PICO_NPK_001",
        "timestamp": 1730317507,
        "soil_moisture": 45.2,
        "soil_temperature": 28.6,
        "humidity": 0.0,
        "light_intensity": 0.0,
        "soil_ph": 6.8,
        "npk": {
            "nitrogen": 125,
            "phosphorus": 48,
            "potassium": 182
        }
    }
    """
    try:
        logger.info(f"📊 Received data from {data.device_id} | Temp: {data.soil_temperature}°C | Moisture: {data.soil_moisture}%")
        
        # Extract NPK values
        nitrogen = data.npk.nitrogen if data.npk else None
        phosphorus = data.npk.phosphorus if data.npk else None
        potassium = data.npk.potassium if data.npk else None
        
        # Store in database
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO sensor_data 
                (device_id, timestamp, soil_moisture, soil_temperature, humidity, 
                 light_intensity, soil_ph, nitrogen, phosphorus, potassium)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.device_id,
                    data.timestamp,
                    data.soil_moisture,
                    data.soil_temperature,
                    data.humidity,
                    data.light_intensity,
                    data.soil_ph,
                    nitrogen,
                    phosphorus,
                    potassium
                )
            )
            await db.commit()
        
        logger.info(f"✅ Data stored successfully for {data.device_id}")
        
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
    """Get latest sensor readings"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            if device_id:
                query = "SELECT * FROM sensor_data WHERE device_id = ? ORDER BY timestamp DESC LIMIT 1"
                cursor = await db.execute(query, (device_id,))
            else:
                query = "SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 10"
                cursor = await db.execute(query)
            
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
            
            logger.info(f"✅ Retrieved {len(data_list)} records")
            return {"status": "success", "count": len(data_list), "data": data_list}
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/sensors/history")
async def get_history(device_id: str, limit: int = 100):
    """Get historical data for device"""
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
            
            logger.info(f"✅ Retrieved {len(data_list)} history records for {device_id}")
            return {
                "status": "success",
                "device_id": device_id,
                "count": len(data_list),
                "data": data_list
            }
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/devices")
async def get_devices():
    """Get all devices that have sent data"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT DISTINCT device_id, MAX(timestamp) as last_timestamp FROM sensor_data GROUP BY device_id"
            )
            rows = await cursor.fetchall()
            
            devices = []
            for row in rows:
                devices.append({
                    "device_id": row[0],
                    "last_timestamp": row[1]
                })
            
            logger.info(f"✅ Found {len(devices)} devices")
            return {"status": "success", "count": len(devices), "devices": devices}
    
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ==================== MAIN ====================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"
    
    logger.info(f"🚀 Starting server on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False
    )

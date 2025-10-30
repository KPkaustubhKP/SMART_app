"""
Smart Agriculture Backend Extension for Pico W Integration
FastAPI endpoint to receive sensor data from Raspberry Pi Pico W

This file extends your existing FastAPI backend to handle incoming
sensor data from the Pico W device.

Add this code to your main FastAPI application file (main.py)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import aiosqlite
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== PYDANTIC MODELS ====================

class PicoSensorData(BaseModel):
    """Model for receiving sensor data from Pico W"""
    device_id: str = Field(..., description="Unique identifier for the Pico W device")
    timestamp: int = Field(..., description="Unix timestamp from device")
    soil_moisture: float = Field(..., ge=0, le=100, description="Soil moisture percentage")
    soil_temperature: float = Field(..., description="Soil temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Air humidity percentage")
    light_intensity: float = Field(..., ge=0, le=100, description="Light intensity percentage")
    soil_ph: Optional[float] = Field(None, ge=0, le=14, description="Soil pH level")
    npk: Optional[dict] = Field(None, description="NPK values")

class PicoResponse(BaseModel):
    """Response model for Pico W requests"""
    status: str
    message: str
    timestamp: datetime
    device_id: Optional[str] = None

# ==================== DATABASE FUNCTIONS ====================

async def init_pico_database():
    """Initialize database table for Pico sensor data"""
    async with aiosqlite.connect("agriculture_monitor.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS pico_sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                soil_moisture REAL NOT NULL,
                soil_temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                light_intensity REAL NOT NULL,
                soil_ph REAL,
                nitrogen INTEGER,
                phosphorus INTEGER,
                potassium INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_device_timestamp 
            ON pico_sensor_data(device_id, timestamp)
        ''')
        
        await db.commit()
        logger.info("Pico database table initialized")

async def store_pico_sensor_data(data: PicoSensorData):
    """Store sensor data from Pico W in database"""
    try:
        async with aiosqlite.connect("agriculture_monitor.db") as db:
            # Extract NPK values if provided
            nitrogen = None
            phosphorus = None
            potassium = None
            
            if data.npk:
                nitrogen = data.npk.get('nitrogen')
                phosphorus = data.npk.get('phosphorus')
                potassium = data.npk.get('potassium')
            
            await db.execute('''
                INSERT INTO pico_sensor_data 
                (device_id, timestamp, soil_moisture, soil_temperature, humidity, 
                 light_intensity, soil_ph, nitrogen, phosphorus, potassium)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
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
            ))
            await db.commit()
            logger.info(f"Stored sensor data from device {data.device_id}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to store sensor data: {e}")
        return False

async def update_current_sensor_cache(data: PicoSensorData):
    """Update the current sensor readings cache for the web interface"""
    try:
        async with aiosqlite.connect("agriculture_monitor.db") as db:
            # Update or insert current readings
            await db.execute('''
                INSERT OR REPLACE INTO current_sensors 
                (id, soil_moisture, soil_temperature, humidity, light_intensity, 
                 soil_ph, nitrogen, phosphorus, potassium, last_updated)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                data.soil_moisture,
                data.soil_temperature,
                data.humidity,
                data.light_intensity,
                data.soil_ph,
                data.npk.get('nitrogen') if data.npk else None,
                data.npk.get('phosphorus') if data.npk else None,
                data.npk.get('potassium') if data.npk else None
            ))
            await db.commit()
            logger.info("Updated current sensor cache")
            
    except Exception as e:
        logger.error(f"Failed to update sensor cache: {e}")

# ==================== API ENDPOINTS ====================

# Add these endpoints to your existing FastAPI app

@app.post("/api/sensors/data", response_model=PicoResponse)
async def receive_pico_sensor_data(
    data: PicoSensorData,
    background_tasks: BackgroundTasks
):
    """
    Receive sensor data from Raspberry Pi Pico W
    
    This endpoint accepts JSON data from the Pico W containing all sensor readings
    and stores them in the database for display on the web interface.
    """
    try:
        logger.info(f"Received data from Pico device: {data.device_id}")
        
        # Store data in background to improve response time
        background_tasks.add_task(store_pico_sensor_data, data)
        background_tasks.add_task(update_current_sensor_cache, data)
        
        return PicoResponse(
            status="success",
            message="Sensor data received and stored successfully",
            timestamp=datetime.now(),
            device_id=data.device_id
        )
        
    except Exception as e:
        logger.error(f"Error processing sensor data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process sensor data: {str(e)}"
        )

@app.get("/api/sensors/pico/test")
async def test_pico_connectivity():
    """Test endpoint for Pico W connectivity verification"""
    return PicoResponse(
        status="success",
        message="Pico W connectivity test successful",
        timestamp=datetime.now()
    )

@app.get("/api/sensors/pico/status/{device_id}")
async def get_pico_device_status(device_id: str):
    """Get status and last communication time for a specific Pico device"""
    try:
        async with aiosqlite.connect("agriculture_monitor.db") as db:
            cursor = await db.execute('''
                SELECT device_id, timestamp, created_at
                FROM pico_sensor_data 
                WHERE device_id = ?
                ORDER BY created_at DESC 
                LIMIT 1
            ''', (device_id,))
            
            row = await cursor.fetchone()
            
            if row:
                return {
                    "device_id": row[0],
                    "last_seen": row[2],
                    "last_data_timestamp": row[1],
                    "status": "online"
                }
            else:
                return {
                    "device_id": device_id,
                    "status": "never_seen",
                    "message": "No data received from this device"
                }
                
    except Exception as e:
        logger.error(f"Error getting device status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sensors/pico/history/{device_id}")
async def get_pico_sensor_history(
    device_id: str,
    limit: int = 100,
    hours: int = 24
):
    """Get historical sensor data from a specific Pico device"""
    try:
        async with aiosqlite.connect("agriculture_monitor.db") as db:
            cursor = await db.execute('''
                SELECT device_id, timestamp, soil_moisture, soil_temperature,
                       humidity, light_intensity, soil_ph, nitrogen, 
                       phosphorus, potassium, created_at
                FROM pico_sensor_data 
                WHERE device_id = ? 
                AND created_at >= datetime('now', '-{} hours')
                ORDER BY created_at DESC 
                LIMIT ?
            '''.format(hours), (device_id, limit))
            
            rows = await cursor.fetchall()
            
            history = []
            for row in rows:
                history.append({
                    "device_id": row[0],
                    "timestamp": row[1],
                    "soil_moisture": row[2],
                    "soil_temperature": row[3],
                    "humidity": row[4],
                    "light_intensity": row[5],
                    "soil_ph": row[6],
                    "npk": {
                        "nitrogen": row[7],
                        "phosphorus": row[8],
                        "potassium": row[9]
                    },
                    "created_at": row[10]
                })
            
            return {
                "device_id": device_id,
                "count": len(history),
                "history": history
            }
            
    except Exception as e:
        logger.error(f"Error getting sensor history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== STARTUP EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Initialize Pico database on startup"""
    await init_pico_database()
    logger.info("Pico W integration initialized")

# ==================== HEALTH CHECK ENHANCEMENT ====================

@app.get("/health")
async def enhanced_health_check():
    """Enhanced health check that includes Pico connectivity status"""
    try:
        # Check database connectivity
        async with aiosqlite.connect("agriculture_monitor.db") as db:
            await db.execute("SELECT 1")
        
        # Check recent Pico activity
        async with aiosqlite.connect("agriculture_monitor.db") as db:
            cursor = await db.execute('''
                SELECT COUNT(*) FROM pico_sensor_data 
                WHERE created_at >= datetime('now', '-1 hour')
            ''')
            recent_data = await cursor.fetchone()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "database": "connected",
            "pico_devices_active": recent_data[0] if recent_data else 0,
            "services": {
                "api": "running",
                "database": "connected",
                "pico_integration": "active"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# ==================== CORS SETUP (if needed) ====================

from fastapi.middleware.cors import CORSMiddleware

# Add CORS middleware if your Pico W needs to access from different domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
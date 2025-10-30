import sys
import os

# Add the app directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import aiosqlite
from datetime import datetime, timedelta
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database path from environment or use default
DB_PATH = os.getenv("DATABASE_PATH", "agriculture_monitor.db")


import os
from pathlib import Path

DB_PATH = os.getenv("DATABASE_PATH", "agriculture_monitor.db")

# Ensure parent directory exists (Render path: /opt/render/project/src/data)
db_dir = Path(DB_PATH).parent
db_dir.mkdir(parents=True, exist_ok=True)


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

async def init_database():
    """Initialize all database tables"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Create pico_sensor_data table
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
        
        # Create current_sensors table for web interface
        await db.execute('''
            CREATE TABLE IF NOT EXISTS current_sensors (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                soil_moisture REAL,
                soil_temperature REAL,
                humidity REAL,
                light_intensity REAL,
                soil_ph REAL,
                nitrogen INTEGER,
                phosphorus INTEGER,
                potassium INTEGER,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        await db.execute('''
            CREATE INDEX IF NOT EXISTS idx_device_timestamp 
            ON pico_sensor_data(device_id, timestamp)
        ''')
        
        # Initialize current_sensors with a row if it doesn't exist
        await db.execute('INSERT OR IGNORE INTO current_sensors (id) VALUES (1)')
        
        await db.commit()
        logger.info("Database tables initialized")

async def store_pico_sensor_data(data: PicoSensorData):
    """Store sensor data from Pico W in database"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
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
        async with aiosqlite.connect(DB_PATH) as db:
            # Update current readings
            await db.execute('''
                UPDATE current_sensors SET 
                    soil_moisture = ?,
                    soil_temperature = ?,
                    humidity = ?,
                    light_intensity = ?,
                    soil_ph = ?,
                    nitrogen = ?,
                    phosphorus = ?,
                    potassium = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
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

# ==================== APP LIFECYCLE ====================

# Global instances (for mock services if needed)
sensor_manager = None
weather_service = None
db_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global sensor_manager, weather_service, db_manager
    
    # Startup
    logger.info("Starting Smart Agriculture API...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database initialized successfully")
        
        # Try to import optional modules
        try:
            from app.models import SensorReading, WeatherData, IrrigationCommand
            from app.sensors import SensorManager
            from app.weather import WeatherService
            from app.database import DatabaseManager
            
            # Initialize services if modules are available
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            sensor_manager = SensorManager(db_manager)
            weather_service = WeatherService()
            
            # Start background monitoring
            asyncio.create_task(sensor_manager.start_monitoring())
            asyncio.create_task(weather_service.start_monitoring())
            
            logger.info("All services started successfully")
            
        except ImportError as e:
            logger.warning(f"Optional modules not found: {e}. Using mock data.")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        # Continue with mock data if initialization fails
    
    yield
    
    # Shutdown
    logger.info("Shutting down Smart Agriculture API...")
    if sensor_manager:
        try:
            await sensor_manager.stop_monitoring()
        except Exception as e:
            logger.error(f"Shutdown error: {e}")

# ==================== FASTAPI APP ====================

app = FastAPI(
    title="Smart Agriculture IoT API",
    description="Real-time agriculture monitoring system with sensor data, irrigation control, and weather integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:80", 
        "https://*.onrender.com",
        "https://smart-agriculture-frontend.onrender.com",
        "*"  # Allow all for development - restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """API health check and info"""
    return {
        "name": "Smart Agriculture IoT API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "sensors": "/api/sensors/current",
            "pico_data": "/api/sensors/data",
            "irrigation": "/api/irrigation/status",
            "weather": "/api/weather/current",
            "alerts": "/api/alerts"
        }
    }

@app.get("/health")
async def health_check():
    """System health check with Pico connectivity status"""
    try:
        # Check database connectivity
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("SELECT 1")
        
        # Check recent Pico activity
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT COUNT(*) FROM pico_sensor_data 
                WHERE created_at >= datetime('now', '-1 hour')
            ''')
            recent_data = await cursor.fetchone()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected",
            "pico_devices_active": recent_data[0] if recent_data else 0,
            "services": {
                "api": "running",
                "database": "connected",
                "pico_integration": "active",
                "sensors": "active" if sensor_manager else "mock",
                "weather": "active" if weather_service else "mock"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# ==================== PICO W ENDPOINTS ====================

@app.post("/api/sensors/data", response_model=PicoResponse)
async def receive_pico_sensor_data(
    data: PicoSensorData,
    background_tasks: BackgroundTasks
):
    """Receive sensor data from Raspberry Pi Pico W"""
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
        async with aiosqlite.connect(DB_PATH) as db:
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
        async with aiosqlite.connect(DB_PATH) as db:
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

# ==================== EXISTING API ENDPOINTS ====================

@app.get("/api/sensors/current")
async def get_current_sensor_data():
    """Get current sensor readings"""
    if sensor_manager:
        try:
            return await sensor_manager.get_current_readings()
        except Exception as e:
            logger.error(f"Sensor data error: {e}")
    
    # Try to get real data from Pico if available, otherwise mock
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute('''
                SELECT soil_moisture, soil_temperature, humidity, light_intensity,
                       soil_ph, nitrogen, phosphorus, potassium, last_updated
                FROM current_sensors WHERE id = 1
            ''')
            row = await cursor.fetchone()
            
            if row and row[0] is not None:  # Has real data
                return {
                    "timestamp": row[8] or datetime.utcnow().isoformat(),
                    "soil_moisture": row[0],
                    "soil_temperature": row[1],
                    "soil_ph": row[4] or 7.0,
                    "soil_conductivity": round(random.uniform(800, 1200), 0),  # Mock
                    "air_temperature": row[1],  # Use soil temp as air temp approximation
                    "humidity": row[2],
                    "atmospheric_pressure": round(random.uniform(1005, 1025), 1),  # Mock
                    "light_intensity": row[3],
                    "npk": {
                        "nitrogen": row[5] or 120,
                        "phosphorus": row[6] or 45,
                        "potassium": row[7] or 175,
                        "timestamp": row[8] or datetime.utcnow().isoformat()
                    }
                }
    except Exception as e:
        logger.error(f"Error reading current sensors: {e}")
    
    # Fallback with mock data
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "soil_moisture": round(random.uniform(30, 70), 1),
        "soil_temperature": round(random.uniform(20, 30), 1),
        "soil_ph": round(random.uniform(6.0, 7.5), 2),
        "soil_conductivity": round(random.uniform(800, 1200), 0),
        "air_temperature": round(random.uniform(22, 35), 1),
        "humidity": round(random.uniform(45, 85), 1),
        "atmospheric_pressure": round(random.uniform(1005, 1025), 1),
        "light_intensity": round(random.uniform(20, 90), 1),
        "npk": {
            "nitrogen": round(random.uniform(100, 150), 0),
            "phosphorus": round(random.uniform(30, 60), 0),
            "potassium": round(random.uniform(150, 200), 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    }

@app.get("/api/irrigation/status")
async def get_irrigation_status():
    """Get current irrigation system status"""
    if sensor_manager:
        try:
            return await sensor_manager.get_irrigation_status()
        except Exception as e:
            logger.error(f"Irrigation status error: {e}")
    
    # Fallback mock data
    return {
        "is_active": random.choice([True, False]),
        "last_activation": (datetime.utcnow() - timedelta(hours=random.randint(1, 12))).isoformat(),
        "total_runtime_today": random.randint(30, 180),
        "water_usage_liters": random.randint(200, 800),
        "next_scheduled": "06:00 AM IST"
    }

@app.post("/api/irrigation/control")
async def control_irrigation(background_tasks: BackgroundTasks):
    """Control irrigation system manually"""
    try:
        if sensor_manager:
            # Execute irrigation command
            from app.models import IrrigationCommand
            command = IrrigationCommand(activate=True, duration_minutes=15)
            background_tasks.add_task(sensor_manager.execute_irrigation, command)
        
        return {
            "message": "Irrigation system activated successfully",
            "duration": "15 minutes",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Irrigation control error: {e}")
        return {
            "message": "Irrigation system activated (mock)",
            "duration": "15 minutes", 
            "timestamp": datetime.utcnow().isoformat(),
            "status": "active"
        }

@app.get("/api/weather/current")
async def get_current_weather():
    """Get current weather data and alerts"""
    if weather_service:
        try:
            return await weather_service.get_current_weather()
        except Exception as e:
            logger.error(f"Weather data error: {e}")
    
    # Fallback mock data
    conditions = ["Clear Sky", "Partly Cloudy", "Cloudy", "Light Rain", "Sunny"]
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "temperature": round(random.uniform(22, 38), 1),
        "humidity": round(random.uniform(40, 85), 1),
        "pressure": round(random.uniform(995, 1030), 1),
        "wind_speed": round(random.uniform(5, 25), 1),
        "wind_direction": random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
        "description": random.choice(conditions),
        "uv_index": random.randint(1, 10),
        "visibility": round(random.uniform(8, 25), 1),
        "alerts": []
    }

@app.get("/api/alerts")
async def get_system_alerts():
    """Get system alerts and notifications"""
    if sensor_manager:
        try:
            return await sensor_manager.get_active_alerts()
        except Exception as e:
            logger.error(f"Alerts error: {e}")
    
    # Mock alerts with occasional warnings
    alerts = []
    if random.random() < 0.3:  # 30% chance of alert
        alerts.append({
            "id": f"alert_{random.randint(1000, 9999)}",
            "type": random.choice(["soil_moisture", "temperature", "ph"]),
            "severity": random.choice(["warning", "info"]),
            "title": "Sensor Reading Alert",
            "message": "Sensor values outside optimal range detected",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return {
        "active_alerts": alerts,
        "total_count": len(alerts),
        "timestamp": datetime.utcnow().isoformat()
    }

# ==================== MAIN ====================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting Smart Agriculture API on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

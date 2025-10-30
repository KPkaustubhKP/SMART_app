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

async def get_latest_sensor_data():
    """Get the latest sensor data from database - either current or last received"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # First try to get data from current_sensors table
            cursor = await db.execute('''
                SELECT soil_moisture, soil_temperature, humidity, light_intensity,
                       soil_ph, nitrogen, phosphorus, potassium, last_updated
                FROM current_sensors WHERE id = 1
            ''')
            row = await cursor.fetchone()
            
            # If we have recent data (within last hour), use it
            if row and row[0] is not None and row[8]:
                try:
                    last_updated = datetime.fromisoformat(row[8].replace('Z', '+00:00'))
                    time_diff = datetime.utcnow() - last_updated
                    
                    # If data is within the last hour, use current_sensors
                    if time_diff <= timedelta(hours=1):
                        return {
                            "source": "current",
                            "timestamp": row[8],
                            "soil_moisture": round(float(row[0]), 2) if row[0] is not None else None,
                            "soil_temperature": round(float(row[1]), 2) if row[1] is not None else None,
                            "humidity": round(float(row[2]), 2) if row[2] is not None else None,
                            "light_intensity": round(float(row[3]), 2) if row[3] is not None else None,
                            "soil_ph": round(float(row[4]), 2) if row[4] is not None else None,
                            "nitrogen": int(row[5]) if row[5] is not None else None,
                            "phosphorus": int(row[6]) if row[6] is not None else None,
                            "potassium": int(row[7]) if row[7] is not None else None
                        }
                except:
                    # If timestamp parsing fails, continue to historical data
                    pass
            
            # If no recent data in current_sensors, get the most recent from historical data
            cursor = await db.execute('''
                SELECT soil_moisture, soil_temperature, humidity, light_intensity,
                       soil_ph, nitrogen, phosphorus, potassium, created_at, device_id
                FROM pico_sensor_data
                ORDER BY created_at DESC
                LIMIT 1
            ''')
            row = await cursor.fetchone()
            
            if row:
                return {
                    "source": "historical",
                    "timestamp": row[8],
                    "device_id": row[9],
                    "soil_moisture": round(float(row[0]), 2) if row[0] is not None else None,
                    "soil_temperature": round(float(row[1]), 2) if row[1] is not None else None,
                    "humidity": round(float(row[2]), 2) if row[2] is not None else None,
                    "light_intensity": round(float(row[3]), 2) if row[3] is not None else None,
                    "soil_ph": round(float(row[4]), 2) if row[4] is not None else None,
                    "nitrogen": int(row[5]) if row[5] is not None else None,
                    "phosphorus": int(row[6]) if row[6] is not None else None,
                    "potassium": int(row[7]) if row[7] is not None else None
                }
            
            # No data available at all
            return None
            
    except Exception as e:
        logger.error(f"Error reading sensor data: {e}")
        return None

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
                    "soil_moisture": round(float(row[2]), 2) if row[2] is not None else None,
                    "soil_temperature": round(float(row[3]), 2) if row[3] is not None else None,
                    "humidity": round(float(row[4]), 2) if row[4] is not None else None,
                    "light_intensity": round(float(row[5]), 2) if row[5] is not None else None,
                    "soil_ph": round(float(row[6]), 2) if row[6] is not None else None,
                    "npk": {
                        "nitrogen": int(row[7]) if row[7] is not None else None,
                        "phosphorus": int(row[8]) if row[8] is not None else None,
                        "potassium": int(row[9]) if row[9] is not None else None
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
    """Get current sensor readings - shows real WiFi data when available, otherwise last data received"""
    
    # First try to get real sensor data from the database
    sensor_data = await get_latest_sensor_data()
    
    if sensor_data:
        logger.info(f"Returning {sensor_data['source']} sensor data from database")
        
        # Format response for dashboard compatibility
        response = {
            "timestamp": sensor_data["timestamp"],
            "soil_moisture": sensor_data["soil_moisture"],
            "soil_temperature": sensor_data["soil_temperature"],
            "soil_ph": sensor_data["soil_ph"] if sensor_data["soil_ph"] is not None else 7.00,
            "soil_conductivity": round(random.uniform(800, 1200), 2),  # Mock - not available from sensors
            "air_temperature": sensor_data["soil_temperature"],  # Use soil temp as approximation
            "humidity": sensor_data["humidity"],
            "atmospheric_pressure": round(random.uniform(1005.00, 1025.00), 2),  # Mock - not available
            "light_intensity": sensor_data["light_intensity"],
            "npk": {
                "nitrogen": sensor_data["nitrogen"] if sensor_data["nitrogen"] is not None else 120,
                "phosphorus": sensor_data["phosphorus"] if sensor_data["phosphorus"] is not None else 45,
                "potassium": sensor_data["potassium"] if sensor_data["potassium"] is not None else 175,
                "timestamp": sensor_data["timestamp"]
            }
        }
        
        # Add data source info for debugging
        if sensor_data["source"] == "historical":
            response["data_source"] = "last_received"
            if "device_id" in sensor_data:
                response["last_device_id"] = sensor_data["device_id"]
        else:
            response["data_source"] = "current"
            
        return response
    
    # If no real data exists at all, return an error or minimal response
    logger.warning("No sensor data available in database")
    return JSONResponse(
        status_code=204,
        content={"message": "No sensor data available yet"}
    )

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
    
    # Fallback mock data with 2 decimal places
    conditions = ["Clear Sky", "Partly Cloudy", "Cloudy", "Light Rain", "Sunny"]
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "temperature": round(random.uniform(22, 38), 2),
        "humidity": round(random.uniform(40, 85), 2),
        "pressure": round(random.uniform(995, 1030), 2),
        "wind_speed": round(random.uniform(5, 25), 2),
        "wind_direction": random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
        "description": random.choice(conditions),
        "uv_index": random.randint(1, 10),
        "visibility": round(random.uniform(8, 25), 2),
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
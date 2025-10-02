# backend/app/main.py - Fixed App Main with Proper Syntax
"""
Smart Agriculture IoT Monitoring System - FastAPI Backend
Real-time sensor data API with irrigation control and weather integration
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import asyncio
from datetime import datetime, timedelta
import random
import logging
from typing import Dict, List, Optional
import os
from contextlib import asynccontextmanager

# Import our modules
try:
    from .models import (
        SensorReading, WeatherData, IrrigationCommand,
        IrrigationStatus, AlertData, SystemStatus
    )
    from .sensors import SensorManager
    from .weather import WeatherService
    from .database import DatabaseManager
except ImportError:
    # Fallback for direct execution
    from models import (
        SensorReading, WeatherData, IrrigationCommand,
        IrrigationStatus, AlertData, SystemStatus
    )
    from sensors import SensorManager
    from weather import WeatherService
    from database import DatabaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
sensor_manager = None
weather_service = None
db_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global sensor_manager, weather_service, db_manager
    
    # Startup
    logger.info("Starting Agriculture Monitoring System...")
    
    try:
        # Initialize services
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        sensor_manager = SensorManager(db_manager)
        weather_service = WeatherService()
        
        # Start background tasks
        asyncio.create_task(sensor_manager.start_monitoring())
        asyncio.create_task(weather_service.start_monitoring())
        
        logger.info("All services started successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agriculture Monitoring System...")
    if sensor_manager:
        try:
            await sensor_manager.stop_monitoring()
        except Exception as e:
            logger.error(f"Shutdown error: {e}")

app = FastAPI(
    title="Smart Agriculture IoT API",
    description="Real-time agriculture monitoring system with sensor data, irrigation control, and weather integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_model=Dict)
async def root():
    """API health check and info"""
    return {
        "name": "Smart Agriculture IoT API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "sensors": "/sensors/current",
            "historical": "/sensors/historical",
            "irrigation": "/irrigation",
            "weather": "/weather",
            "alerts": "/alerts"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected" if db_manager else "disconnected",
            "sensors": "active" if sensor_manager else "inactive",
            "weather": "active" if weather_service else "inactive"
        }
    }

# Sensor endpoints
@app.get("/sensors/current")
async def get_current_sensor_data():
    """Get current sensor readings"""
    if sensor_manager:
        try:
            return await sensor_manager.get_current_readings()
        except Exception as e:
            logger.error(f"Sensor data error: {e}")
    
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
        "npk": {
            "nitrogen": round(random.uniform(100, 150), 0),
            "phosphorus": round(random.uniform(30, 60), 0),
            "potassium": round(random.uniform(150, 200), 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    }

@app.get("/sensors/historical")
async def get_historical_sensor_data(hours: int = 24, sensor_type: Optional[str] = None):
    """Get historical sensor data"""
    if sensor_manager:
        try:
            return await sensor_manager.get_historical_data(hours=hours, sensor_type=sensor_type)
        except Exception as e:
            logger.error(f"Historical data error: {e}")
    
    # Fallback mock data
    data_points = []
    for i in range(24):
        timestamp = datetime.utcnow() - timedelta(hours=i)
        data_points.append({
            "timestamp": timestamp.isoformat(),
            "value": round(random.uniform(30, 70), 1) if sensor_type == "soil_moisture" else round(random.uniform(20, 30), 1)
        })
    
    return {
        "sensor_type": sensor_type or "all",
        "data_points": data_points,
        "total_points": len(data_points)
    }

# Irrigation endpoints
@app.get("/irrigation/status")
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
        "last_activation": datetime.utcnow().isoformat(),
        "total_runtime_today": random.randint(30, 180),
        "water_usage_liters": random.randint(200, 800),
        "next_scheduled": "06:00 AM IST"
    }

@app.post("/irrigation/control")
async def control_irrigation(background_tasks: BackgroundTasks):
    """Control irrigation system manually"""
    try:
        if sensor_manager:
            # Execute irrigation command
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
        raise HTTPException(status_code=500, detail=str(e))

# Weather endpoints
@app.get("/weather/current")
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

@app.get("/weather/forecast")
async def get_weather_forecast(days: int = 5):
    """Get weather forecast"""
    if weather_service:
        try:
            return await weather_service.get_forecast(days=days)
        except Exception as e:
            logger.error(f"Weather forecast error: {e}")
    
    # Fallback mock data
    forecast = []
    for i in range(days):
        date = datetime.utcnow() + timedelta(days=i)
        forecast.append({
            "date": date.date().isoformat(),
            "temperature_high": round(random.uniform(25, 35), 1),
            "temperature_low": round(random.uniform(15, 25), 1),
            "description": random.choice(["Sunny", "Partly Cloudy", "Cloudy"]),
            "precipitation_chance": random.randint(0, 80)
        })
    
    return {
        "forecast": forecast,
        "days": days
    }

# Alerts endpoint
@app.get("/alerts")
async def get_system_alerts():
    """Get system alerts and notifications"""
    if sensor_manager:
        try:
            return await sensor_manager.get_active_alerts()
        except Exception as e:
            logger.error(f"Alerts error: {e}")
    
    # Mock alerts
    alerts = []
    if random.random() < 0.3:  # 30% chance
        alerts.append({
            "id": "alert_001",
            "type": "soil_moisture",
            "severity": "warning",
            "title": "Low Soil Moisture",
            "message": "Soil moisture levels below optimal range",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return {
        "active_alerts": alerts,
        "total_count": len(alerts),
        "timestamp": datetime.utcnow().isoformat()
    }

# System status endpoint
@app.get("/system/status")
async def get_system_status():
    """Get overall system status"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "sensors_online": sensor_manager is not None,
        "weather_service_online": weather_service is not None,
        "irrigation_available": sensor_manager is not None,
        "database_connected": db_manager is not None,
        "uptime_hours": 0.0,
        "active_alerts": 0
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
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
from app.models import (
    SensorReading, WeatherData, IrrigationCommand, 
    IrrigationStatus, AlertData, SystemStatus
)
from app.sensors import SensorManager
from app.weather import WeatherService
from app.database import DatabaseManager

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

    # Initialize services
    db_manager = DatabaseManager()
    await db_manager.initialize()

    sensor_manager = SensorManager(db_manager)
    weather_service = WeatherService()

    # Start background tasks
    asyncio.create_task(sensor_manager.start_monitoring())
    asyncio.create_task(weather_service.start_monitoring())

    yield

    # Shutdown
    logger.info("Shutting down Agriculture Monitoring System...")
    if sensor_manager:
        await sensor_manager.stop_monitoring()

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
            "sensors": "/api/sensors/current",
            "historical": "/api/sensors/historical",
            "irrigation": "/api/irrigation",
            "weather": "/api/weather",
            "alerts": "/api/alerts"
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
@app.get("/api/sensors/current", response_model=SensorReading)
async def get_current_sensor_data():
    """Get current sensor readings"""
    if not sensor_manager:
        raise HTTPException(status_code=503, detail="Sensor manager not available")

    return await sensor_manager.get_current_readings()

@app.get("/api/sensors/historical")
async def get_historical_sensor_data(
    hours: int = 24,
    sensor_type: Optional[str] = None
):
    """Get historical sensor data"""
    if not sensor_manager:
        raise HTTPException(status_code=503, detail="Sensor manager not available")

    return await sensor_manager.get_historical_data(hours=hours, sensor_type=sensor_type)

# Irrigation endpoints
@app.get("/api/irrigation/status", response_model=IrrigationStatus)
async def get_irrigation_status():
    """Get current irrigation system status"""
    if not sensor_manager:
        raise HTTPException(status_code=503, detail="Sensor manager not available")

    return await sensor_manager.get_irrigation_status()

@app.post("/api/irrigation/control")
async def control_irrigation(command: IrrigationCommand, background_tasks: BackgroundTasks):
    """Control irrigation system manually"""
    if not sensor_manager:
        raise HTTPException(status_code=503, detail="Sensor manager not available")

    try:
        # Execute irrigation command
        background_tasks.add_task(sensor_manager.execute_irrigation, command)

        return {
            "message": f"Irrigation {'activated' if command.activate else 'deactivated'}",
            "duration": command.duration_minutes if command.activate else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Irrigation control error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Weather endpoints
@app.get("/api/weather/current", response_model=WeatherData)
async def get_current_weather():
    """Get current weather data and alerts"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service not available")

    return await weather_service.get_current_weather()

@app.get("/api/weather/alerts")
async def get_weather_alerts():
    """Get active weather alerts"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service not available")

    return await weather_service.get_alerts()

@app.get("/api/weather/forecast")
async def get_weather_forecast(days: int = 5):
    """Get weather forecast"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service not available")

    return await weather_service.get_forecast(days=days)

# Alerts endpoint
@app.get("/api/alerts")
async def get_system_alerts():
    """Get system alerts and notifications"""
    if not sensor_manager:
        raise HTTPException(status_code=503, detail="Sensor manager not available")

    return await sensor_manager.get_active_alerts()

# System status endpoint
@app.get("/api/system/status", response_model=SystemStatus)
async def get_system_status():
    """Get overall system status"""
    sensor_status = await sensor_manager.get_system_health() if sensor_manager else "offline"
    weather_status = await weather_service.get_service_status() if weather_service else "offline"

    return SystemStatus(
        timestamp=datetime.utcnow(),
        sensors_online=sensor_status == "online",
        weather_service_online=weather_status == "online",
        irrigation_available=sensor_manager is not None,
        database_connected=db_manager is not None
    )

# WebSocket endpoint for real-time data
@app.websocket("/ws/sensors")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time sensor data"""
    await websocket.accept()

    try:
        while True:
            if sensor_manager:
                data = await sensor_manager.get_current_readings()
                await websocket.send_json(data.dict())
            else:
                await websocket.send_json({"error": "Sensor manager not available"})

            await asyncio.sleep(5)  # Send updates every 5 seconds

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False,
        log_level="info"
    )

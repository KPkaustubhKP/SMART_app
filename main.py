"""
Smart Agriculture IoT Monitoring System - FastAPI Backend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from datetime import datetime
import random
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Smart Agriculture IoT API",
    description="Real-time agriculture monitoring system",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """API health check and info"""
    return {
        "name": "Smart Agriculture IoT API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }

@app.get("/api/sensors/current")
async def get_current_sensor_data():
    """Get current sensor readings"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "soil_moisture": round(random.uniform(30, 70), 1),
        "soil_temperature": round(random.uniform(18, 35), 1),
        "soil_ph": round(random.uniform(6.0, 7.5), 2),
        "soil_conductivity": round(random.uniform(100, 2000), 0),
        "air_temperature": round(random.uniform(20, 40), 1),
        "humidity": round(random.uniform(40, 80), 1),
        "atmospheric_pressure": round(random.uniform(980, 1030), 1),
        "npk": {
            "nitrogen": round(random.uniform(100, 150), 0),
            "phosphorus": round(random.uniform(30, 60), 0),
            "potassium": round(random.uniform(150, 200), 0)
        }
    }

@app.get("/api/weather/current")
async def get_current_weather():
    """Get current weather data"""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "temperature": round(random.uniform(20, 35), 1),
        "humidity": round(random.uniform(40, 80), 1),
        "pressure": round(random.uniform(980, 1030), 1),
        "wind_speed": round(random.uniform(5, 25), 1),
        "description": "Partly Cloudy",
        "alerts": []
    }

@app.post("/api/irrigation/control")
async def control_irrigation():
    """Control irrigation system"""
    return {
        "message": "Irrigation system activated",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

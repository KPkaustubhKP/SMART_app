from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from datetime import datetime
import random

app = FastAPI(
    title="Smart Agriculture IoT API",
    description="Real-time agriculture monitoring system with sensor data and irrigation control",
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
    """API root endpoint"""
    return {
        "name": "Smart Agriculture IoT API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "docs_url": "/docs",
        "endpoints": {
            "current_sensors": "/api/sensors/current",
            "weather": "/api/weather/current",
            "irrigation": "/api/irrigation/control"
        }
    }

@app.get("/health")
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "running"
    }

@app.get("/api/sensors/current")
async def get_current_sensor_data():
    """Get current sensor readings with realistic data"""
    # Simulate time-based variations
    hour = datetime.now().hour
    temp_variation = 5 * (hour - 12) / 12  # Temperature variation based on time
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "soil_moisture": round(random.uniform(30, 70) + random.gauss(0, 5), 1),
        "soil_temperature": round(25 + temp_variation + random.gauss(0, 2), 1),
        "soil_ph": round(random.uniform(6.2, 7.3), 2),
        "soil_conductivity": round(random.uniform(800, 1200), 0),
        "air_temperature": round(28 + temp_variation + random.gauss(0, 3), 1),
        "humidity": round(random.uniform(45, 85), 1),
        "atmospheric_pressure": round(random.uniform(1005, 1025), 1),
        "npk": {
            "nitrogen": round(random.uniform(100, 150), 0),
            "phosphorus": round(random.uniform(30, 60), 0),
            "potassium": round(random.uniform(150, 200), 0)
        }
    }

@app.get("/api/weather/current")
async def get_current_weather():
    """Get current weather data"""
    conditions = [
        "Clear Sky", "Partly Cloudy", "Cloudy", "Light Rain",
        "Scattered Clouds", "Sunny", "Overcast"
    ]
    
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

@app.post("/api/irrigation/control")
async def control_irrigation():
    """Control irrigation system - manual activation"""
    return {
        "message": "Irrigation system activated successfully",
        "timestamp": datetime.utcnow().isoformat(),
        "duration": "15 minutes",
        "status": "active",
        "estimated_water_usage": "125 liters"
    }

@app.get("/api/irrigation/status")
async def get_irrigation_status():
    """Get current irrigation system status"""
    return {
        "is_active": random.choice([True, False]),
        "last_activation": datetime.utcnow().isoformat(),
        "total_runtime_today": random.randint(30, 180),
        "water_usage_today": random.randint(200, 800),
        "next_scheduled": "06:00 AM IST"
    }

@app.get("/api/alerts")
async def get_system_alerts():
    """Get system alerts and notifications"""
    alerts = []
    
    # Randomly generate some alerts for demo
    if random.random() < 0.3:  # 30% chance
        alerts.append({
            "id": "alert_001",
            "type": "soil_moisture",
            "severity": "warning",
            "message": "Soil moisture levels below optimal range",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    return {
        "active_alerts": alerts,
        "total_count": len(alerts),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port, reload=False)

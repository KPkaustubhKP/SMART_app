"""
Weather service for agriculture monitoring system
Provides weather data and alerts
"""
import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from app.models import WeatherData, WeatherAlert

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.monitoring_active = False
        self.current_weather = None

    async def start_monitoring(self):
        """Start weather monitoring"""
        self.monitoring_active = True
        logger.info("Starting weather monitoring...")
        asyncio.create_task(self._weather_update_loop())

    async def stop_monitoring(self):
        """Stop weather monitoring"""
        self.monitoring_active = False
        logger.info("Stopping weather monitoring...")

    async def _weather_update_loop(self):
        """Weather update loop"""
        while self.monitoring_active:
            try:
                self._generate_weather_data()
                await asyncio.sleep(600)  # Update every 10 minutes
            except Exception as e:
                logger.error(f"Error in weather update loop: {e}")
                await asyncio.sleep(60)

    def _generate_weather_data(self):
        """Generate mock weather data"""
        conditions = ["Clear Sky", "Partly Cloudy", "Cloudy", "Light Rain", "Sunny", "Overcast"]
        wind_directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

        self.current_weather = {
            "timestamp": datetime.utcnow().isoformat(),
            "temperature": round(random.uniform(22, 38), 1),
            "humidity": round(random.uniform(40, 85), 1),
            "pressure": round(random.uniform(995, 1030), 1),
            "wind_speed": round(random.uniform(5, 25), 1),
            "wind_direction": random.choice(wind_directions),
            "description": random.choice(conditions),
            "uv_index": random.randint(1, 10),
            "visibility": round(random.uniform(8, 25), 1),
            "alerts": []
        }

    async def get_current_weather(self) -> Dict:
        """Get current weather data"""
        if self.current_weather is None:
            self._generate_weather_data()
        return self.current_weather

    async def get_forecast(self, days: int = 5) -> Dict:
        """Get weather forecast"""
        forecast = []
        for i in range(days):
            date = datetime.utcnow() + timedelta(days=i)
            forecast.append({
                "date": date.date().isoformat(),
                "temperature_high": round(random.uniform(25, 35), 1),
                "temperature_low": round(random.uniform(15, 25), 1),
                "description": random.choice(["Sunny", "Partly Cloudy", "Cloudy", "Light Rain"]),
                "precipitation_chance": random.randint(0, 80)
            })

        return {
            "forecast": forecast,
            "days": days
        }

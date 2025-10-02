"""
Weather service integration for agriculture monitoring
Integrates with OpenWeatherMap API and provides weather alerts
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import json

from app.models import WeatherData, WeatherAlert, WeatherAlertType, AlertSeverity

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "demo_key")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.location = {
            "lat": os.getenv("FARM_LATITUDE", "40.7128"),
            "lon": os.getenv("FARM_LONGITUDE", "-74.0060")
        }
        self.current_weather = None
        self.weather_alerts = []
        self.monitoring_active = False

        # Generate initial mock data
        self._generate_mock_weather_data()

    async def start_monitoring(self):
        """Start weather monitoring"""
        self.monitoring_active = True
        logger.info("Starting weather monitoring...")

        # Start weather monitoring task
        asyncio.create_task(self._weather_monitoring_loop())

    async def stop_monitoring(self):
        """Stop weather monitoring"""
        self.monitoring_active = False
        logger.info("Stopping weather monitoring...")

    async def _weather_monitoring_loop(self):
        """Main weather monitoring loop"""
        while self.monitoring_active:
            try:
                # Fetch weather data
                if self.api_key != "demo_key":
                    await self._fetch_real_weather_data()
                else:
                    await self._update_mock_weather_data()

                # Check for severe weather alerts
                await self._check_weather_alerts()

                # Update every 10 minutes
                await asyncio.sleep(600)

            except Exception as e:
                logger.error(f"Error in weather monitoring loop: {e}")
                await asyncio.sleep(60)

    async def _fetch_real_weather_data(self):
        """Fetch real weather data from OpenWeatherMap API"""
        try:
            async with aiohttp.ClientSession() as session:
                # Current weather
                current_url = f"{self.base_url}/weather"
                params = {
                    "lat": self.location["lat"],
                    "lon": self.location["lon"],
                    "appid": self.api_key,
                    "units": "metric"
                }

                async with session.get(current_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.current_weather = self._parse_current_weather(data)
                    else:
                        logger.warning(f"Weather API request failed: {response.status}")

                # Weather alerts
                alerts_url = f"{self.base_url}/onecall"
                alerts_params = {
                    "lat": self.location["lat"],
                    "lon": self.location["lon"],
                    "appid": self.api_key,
                    "exclude": "minutely,hourly,daily",
                    "units": "metric"
                }

                async with session.get(alerts_url, params=alerts_params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "alerts" in data:
                            self.weather_alerts = self._parse_weather_alerts(data["alerts"])

        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            # Fall back to mock data
            await self._update_mock_weather_data()

    def _parse_current_weather(self, data: dict) -> WeatherData:
        """Parse OpenWeatherMap current weather response"""
        return WeatherData(
            timestamp=datetime.utcnow(),
            temperature=data["main"]["temp"],
            humidity=data["main"]["humidity"],
            pressure=data["main"]["pressure"],
            wind_speed=data.get("wind", {}).get("speed", 0) * 3.6,  # Convert m/s to km/h
            wind_direction=self._degrees_to_direction(data.get("wind", {}).get("deg", 0)),
            description=data["weather"][0]["description"].title(),
            uv_index=0,  # Requires separate UV API call
            visibility=data.get("visibility", 10000) / 1000,  # Convert m to km
            alerts=self.weather_alerts
        )

    def _parse_weather_alerts(self, alerts_data: List[dict]) -> List[WeatherAlert]:
        """Parse weather alerts from API response"""
        parsed_alerts = []

        for alert in alerts_data:
            alert_type = self._classify_alert_type(alert.get("event", "").lower())
            severity = self._determine_alert_severity(alert.get("severity", "").lower())

            parsed_alerts.append(WeatherAlert(
                id=f"alert_{datetime.utcnow().timestamp()}",
                type=alert_type,
                severity=severity,
                title=alert.get("event", "Weather Alert"),
                message=alert.get("description", "Severe weather conditions expected"),
                start_time=datetime.fromtimestamp(alert.get("start", datetime.utcnow().timestamp())),
                end_time=datetime.fromtimestamp(alert.get("end", datetime.utcnow().timestamp())) if alert.get("end") else None,
                affected_areas=alert.get("areas", [])
            ))

        return parsed_alerts

    def _classify_alert_type(self, event: str) -> WeatherAlertType:
        """Classify alert type from event description"""
        if "thunder" in event or "storm" in event:
            return WeatherAlertType.THUNDERSTORM
        elif "rain" in event or "shower" in event:
            return WeatherAlertType.HEAVY_RAIN
        elif "wind" in event:
            return WeatherAlertType.HIGH_WINDS
        elif "flood" in event:
            return WeatherAlertType.FLOOD
        elif "hail" in event:
            return WeatherAlertType.HAIL
        elif "frost" in event or "freeze" in event:
            return WeatherAlertType.FROST
        elif "drought" in event:
            return WeatherAlertType.DROUGHT
        else:
            return WeatherAlertType.THUNDERSTORM

    def _determine_alert_severity(self, severity: str) -> AlertSeverity:
        """Determine alert severity from API data"""
        severity_map = {
            "minor": AlertSeverity.LOW,
            "moderate": AlertSeverity.MODERATE,
            "severe": AlertSeverity.HIGH,
            "extreme": AlertSeverity.CRITICAL
        }
        return severity_map.get(severity, AlertSeverity.MODERATE)

    def _degrees_to_direction(self, degrees: float) -> str:
        """Convert wind direction from degrees to compass direction"""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(degrees / 22.5) % 16
        return directions[index]

    def _generate_mock_weather_data(self):
        """Generate realistic mock weather data"""
        import random

        # Base weather conditions
        base_temp = 25.0 + random.gauss(0, 5)
        base_humidity = 60 + random.gauss(0, 10)
        base_pressure = 1013 + random.gauss(0, 10)

        self.current_weather = WeatherData(
            timestamp=datetime.utcnow(),
            temperature=round(base_temp, 1),
            humidity=max(20, min(100, round(base_humidity, 0))),
            pressure=round(base_pressure, 1),
            wind_speed=round(random.uniform(5, 25), 1),
            wind_direction=random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
            description=random.choice([
                "Clear Sky", "Partly Cloudy", "Cloudy", "Light Rain", 
                "Overcast", "Scattered Clouds", "Sunny"
            ]),
            uv_index=random.randint(1, 10),
            visibility=round(random.uniform(8, 25), 1),
            alerts=self._generate_mock_alerts()
        )

    def _generate_mock_alerts(self) -> List[WeatherAlert]:
        """Generate mock weather alerts for demo purposes"""
        alerts = []

        # Randomly generate alerts (30% chance)
        if random.random() < 0.3:
            alert_types = [
                (WeatherAlertType.THUNDERSTORM, "Thunderstorm Warning", 
                 "Thunderstorms with heavy rain and strong winds expected. Secure outdoor equipment."),
                (WeatherAlertType.HEAVY_RAIN, "Heavy Rain Alert", 
                 "Heavy rainfall forecast. Risk of waterlogging in low-lying areas."),
                (WeatherAlertType.HIGH_WINDS, "High Wind Warning", 
                 "Strong winds expected. Potential for crop damage and equipment disruption."),
                (WeatherAlertType.HAIL, "Hail Alert", 
                 "Hailstorm possible. Protect sensitive crops and equipment."),
                (WeatherAlertType.FROST, "Frost Advisory", 
                 "Frost conditions expected overnight. Protect frost-sensitive plants.")
            ]

            alert_type, title, message = random.choice(alert_types)
            severity = random.choice([AlertSeverity.LOW, AlertSeverity.MODERATE, AlertSeverity.HIGH])

            alerts.append(WeatherAlert(
                id=f"mock_alert_{datetime.utcnow().timestamp()}",
                type=alert_type,
                severity=severity,
                title=title,
                message=message,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow() + timedelta(hours=random.randint(2, 12)),
                affected_areas=["Farm Area", "Surrounding Region"]
            ))

        return alerts

    async def _update_mock_weather_data(self):
        """Update mock weather data with realistic variations"""
        if self.current_weather:
            # Small variations to simulate real-time changes
            import random

            # Update temperature (small random walk)
            temp_change = random.gauss(0, 0.5)
            new_temp = self.current_weather.temperature + temp_change
            self.current_weather.temperature = round(max(-10, min(50, new_temp)), 1)

            # Update humidity (inversely related to temperature changes)
            humidity_change = -temp_change * 2 + random.gauss(0, 2)
            new_humidity = self.current_weather.humidity + humidity_change
            self.current_weather.humidity = max(20, min(100, round(new_humidity, 0)))

            # Update pressure (slow changes)
            pressure_change = random.gauss(0, 0.5)
            new_pressure = self.current_weather.pressure + pressure_change
            self.current_weather.pressure = round(max(980, min(1050, new_pressure)), 1)

            # Update wind (more variable)
            wind_change = random.gauss(0, 2)
            new_wind = self.current_weather.wind_speed + wind_change
            self.current_weather.wind_speed = round(max(0, min(100, new_wind)), 1)

            # Update timestamp
            self.current_weather.timestamp = datetime.utcnow()

            # Occasionally update alerts
            if random.random() < 0.1:  # 10% chance to update alerts
                self.weather_alerts = self._generate_mock_alerts()
                self.current_weather.alerts = self.weather_alerts

    async def _check_weather_alerts(self):
        """Check for weather conditions that require alerts"""
        if not self.current_weather:
            return

        # Generate alerts based on current conditions
        new_alerts = []

        # High wind alert
        if self.current_weather.wind_speed > 50:
            new_alerts.append(WeatherAlert(
                id=f"wind_alert_{datetime.utcnow().timestamp()}",
                type=WeatherAlertType.HIGH_WINDS,
                severity=AlertSeverity.HIGH,
                title="High Wind Warning",
                message=f"Very strong winds detected: {self.current_weather.wind_speed} km/h. Secure equipment and protect crops.",
                start_time=datetime.utcnow(),
                end_time=None,
                affected_areas=["Farm Area"]
            ))

        # Low pressure alert (potential storms)
        if self.current_weather.pressure < 995:
            new_alerts.append(WeatherAlert(
                id=f"pressure_alert_{datetime.utcnow().timestamp()}",
                type=WeatherAlertType.THUNDERSTORM,
                severity=AlertSeverity.MODERATE,
                title="Low Pressure System",
                message=f"Low atmospheric pressure detected: {self.current_weather.pressure} hPa. Potential for severe weather.",
                start_time=datetime.utcnow(),
                end_time=None,
                affected_areas=["Farm Area"]
            ))

        # Update alerts if new ones are generated
        if new_alerts:
            self.weather_alerts.extend(new_alerts)
            self.current_weather.alerts = self.weather_alerts

    async def get_current_weather(self) -> WeatherData:
        """Get current weather data"""
        if self.current_weather is None:
            self._generate_mock_weather_data()
        return self.current_weather

    async def get_alerts(self) -> List[WeatherAlert]:
        """Get active weather alerts"""
        # Filter out expired alerts
        current_time = datetime.utcnow()
        active_alerts = []

        for alert in self.weather_alerts:
            if alert.end_time is None or alert.end_time > current_time:
                active_alerts.append(alert)

        return active_alerts

    async def get_forecast(self, days: int = 5) -> Dict:
        """Get weather forecast (mock implementation)"""
        # Generate mock forecast data
        forecast_days = []

        for i in range(days):
            forecast_date = datetime.utcnow().date() + timedelta(days=i+1)

            # Generate realistic forecast values
            base_temp = self.current_weather.temperature if self.current_weather else 25
            temp_variation = random.gauss(0, 3)

            forecast_days.append({
                "date": forecast_date.isoformat(),
                "temperature_high": round(base_temp + temp_variation + random.uniform(2, 8), 1),
                "temperature_low": round(base_temp + temp_variation - random.uniform(2, 8), 1),
                "humidity": random.randint(40, 85),
                "precipitation_chance": random.randint(0, 100),
                "wind_speed": round(random.uniform(10, 30), 1),
                "description": random.choice([
                    "Sunny", "Partly Cloudy", "Cloudy", "Light Rain", 
                    "Scattered Showers", "Clear", "Overcast"
                ])
            })

        return {
            "location": self.location,
            "forecast_days": forecast_days,
            "generated_at": datetime.utcnow().isoformat()
        }

    async def get_service_status(self) -> str:
        """Get weather service status"""
        if self.monitoring_active and self.current_weather:
            return "online"
        return "offline"

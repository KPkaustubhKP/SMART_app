"""
Sensor data simulation and management for IoT agriculture system
Simulates real sensor readings with realistic variations and trends
"""

import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import uuid

from app.models import (
    SensorReading, NPKReading, IrrigationStatus, IrrigationCommand,
    AlertData, AlertSeverity, SensorType, ThresholdSettings
)

logger = logging.getLogger(__name__)

class SensorManager:
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self.monitoring_active = False
        self.current_readings = None
        self.irrigation_status = IrrigationStatus(is_active=False)
        self.alerts: List[AlertData] = []
        self.thresholds = ThresholdSettings()

        # Simulation parameters for realistic sensor behavior
        self.base_values = {
            'soil_moisture': 50.0,
            'soil_temperature': 24.0,
            'soil_ph': 6.8,
            'soil_conductivity': 850.0,
            'air_temperature': 28.0,
            'humidity': 65.0,
            'atmospheric_pressure': 1013.2,
            'nitrogen': 120.0,
            'phosphorus': 45.0,
            'potassium': 180.0
        }

        # Trend factors for daily variations
        self.trends = {param: 0.0 for param in self.base_values.keys()}

        # Initialize with first reading
        self._generate_realistic_reading()

    async def start_monitoring(self):
        """Start the sensor monitoring loop"""
        self.monitoring_active = True
        logger.info("Starting sensor monitoring...")

        # Start monitoring tasks
        asyncio.create_task(self._sensor_reading_loop())
        asyncio.create_task(self._alert_monitoring_loop())
        asyncio.create_task(self._irrigation_management_loop())

    async def stop_monitoring(self):
        """Stop sensor monitoring"""
        self.monitoring_active = False
        logger.info("Stopping sensor monitoring...")

    async def _sensor_reading_loop(self):
        """Main sensor reading loop"""
        while self.monitoring_active:
            try:
                # Generate new reading
                self._generate_realistic_reading()

                # Store in database if available
                if self.db_manager:
                    await self.db_manager.store_sensor_reading(self.current_readings)

                # Check for threshold violations
                await self._check_thresholds()

                # Wait for next reading (every 30 seconds)
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"Error in sensor reading loop: {e}")
                await asyncio.sleep(5)

    def _generate_realistic_reading(self):
        """Generate realistic sensor readings with natural variations"""
        now = datetime.utcnow()

        # Time-based variations (daily cycles)
        hour_of_day = now.hour
        day_progress = hour_of_day / 24.0

        # Daily temperature cycle (cooler at night, warmer during day)
        temp_variation = math.sin((day_progress - 0.25) * 2 * math.pi) * 5

        # Humidity inversely related to temperature
        humidity_variation = -temp_variation * 0.8

        # Soil moisture decreases during day (evaporation)
        moisture_variation = -abs(math.sin(day_progress * math.pi)) * 10

        # Add random variations to simulate real sensor noise
        readings = {}

        # Soil measurements
        readings['soil_moisture'] = max(10, min(90, 
            self.base_values['soil_moisture'] + moisture_variation + 
            random.gauss(0, 2) + self.trends['soil_moisture']
        ))

        readings['soil_temperature'] = max(5, min(45,
            self.base_values['soil_temperature'] + temp_variation * 0.3 + 
            random.gauss(0, 0.5) + self.trends['soil_temperature']
        ))

        readings['soil_ph'] = max(4.0, min(9.0,
            self.base_values['soil_ph'] + random.gauss(0, 0.1) + 
            self.trends['soil_ph']
        ))

        readings['soil_conductivity'] = max(100, min(3000,
            self.base_values['soil_conductivity'] + random.gauss(0, 20) + 
            self.trends['soil_conductivity']
        ))

        # Atmospheric measurements
        readings['air_temperature'] = max(-10, min(50,
            self.base_values['air_temperature'] + temp_variation + 
            random.gauss(0, 1) + self.trends['air_temperature']
        ))

        readings['humidity'] = max(20, min(95,
            self.base_values['humidity'] + humidity_variation + 
            random.gauss(0, 3) + self.trends['humidity']
        ))

        readings['atmospheric_pressure'] = max(980, min(1040,
            self.base_values['atmospheric_pressure'] + random.gauss(0, 2) + 
            self.trends['atmospheric_pressure']
        ))

        # NPK readings (change more slowly)
        npk_readings = NPKReading(
            nitrogen=max(50, min(250,
                self.base_values['nitrogen'] + random.gauss(0, 2) + 
                self.trends['nitrogen']
            )),
            phosphorus=max(20, min(80,
                self.base_values['phosphorus'] + random.gauss(0, 1) + 
                self.trends['phosphorus']
            )),
            potassium=max(100, min(300,
                self.base_values['potassium'] + random.gauss(0, 3) + 
                self.trends['potassium']
            )),
            timestamp=now
        )

        # Create sensor reading
        self.current_readings = SensorReading(
            timestamp=now,
            soil_moisture=round(readings['soil_moisture'], 1),
            soil_temperature=round(readings['soil_temperature'], 1),
            soil_ph=round(readings['soil_ph'], 2),
            soil_conductivity=round(readings['soil_conductivity'], 0),
            air_temperature=round(readings['air_temperature'], 1),
            humidity=round(readings['humidity'], 1),
            atmospheric_pressure=round(readings['atmospheric_pressure'], 1),
            npk=npk_readings
        )

        # Gradually adjust trends (environmental changes over time)
        for param in self.trends:
            self.trends[param] += random.gauss(0, 0.01)
            self.trends[param] = max(-5, min(5, self.trends[param]))  # Limit trends

    async def get_current_readings(self) -> SensorReading:
        """Get the current sensor readings"""
        if self.current_readings is None:
            self._generate_realistic_reading()
        return self.current_readings

    async def get_historical_data(self, hours: int = 24, sensor_type: Optional[str] = None) -> Dict:
        """Get historical sensor data"""
        if self.db_manager:
            return await self.db_manager.get_historical_readings(hours, sensor_type)
        else:
            # Generate mock historical data
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            # Generate hourly data points
            data_points = []
            current_time = start_time

            while current_time <= end_time:
                # Simulate historical readings
                temp_reading = self._generate_mock_historical_reading(current_time)
                data_points.append({
                    'timestamp': current_time.isoformat(),
                    **temp_reading
                })
                current_time += timedelta(hours=1)

            return {
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'data_points': data_points,
                'total_points': len(data_points)
            }

    def _generate_mock_historical_reading(self, timestamp: datetime) -> Dict:
        """Generate a mock historical reading for a specific timestamp"""
        hour_of_day = timestamp.hour
        day_progress = hour_of_day / 24.0

        # Simplified historical data generation
        temp_variation = math.sin((day_progress - 0.25) * 2 * math.pi) * 4

        return {
            'soil_moisture': round(50 + random.gauss(0, 5) - abs(math.sin(day_progress * math.pi)) * 8, 1),
            'soil_temperature': round(24 + temp_variation * 0.3 + random.gauss(0, 0.5), 1),
            'air_temperature': round(28 + temp_variation + random.gauss(0, 1), 1),
            'humidity': round(65 - temp_variation * 0.8 + random.gauss(0, 3), 1),
            'soil_ph': round(6.8 + random.gauss(0, 0.1), 2),
            'atmospheric_pressure': round(1013 + random.gauss(0, 2), 1)
        }

    async def _check_thresholds(self):
        """Check sensor readings against thresholds and generate alerts"""
        if not self.current_readings:
            return

        current_alerts = []

        # Check each sensor against thresholds
        checks = [
            ('soil_moisture', self.current_readings.soil_moisture, self.thresholds.soil_moisture),
            ('soil_temperature', self.current_readings.soil_temperature, self.thresholds.soil_temperature),
            ('soil_ph', self.current_readings.soil_ph, self.thresholds.soil_ph),
            ('air_temperature', self.current_readings.air_temperature, self.thresholds.air_temperature),
            ('humidity', self.current_readings.humidity, self.thresholds.humidity),
            ('nitrogen', self.current_readings.npk.nitrogen, self.thresholds.npk_nitrogen),
            ('phosphorus', self.current_readings.npk.phosphorus, self.thresholds.npk_phosphorus),
            ('potassium', self.current_readings.npk.potassium, self.thresholds.npk_potassium)
        ]

        for sensor_name, value, threshold in checks:
            if value < threshold['min']:
                severity = AlertSeverity.HIGH if value < threshold['min'] * 0.8 else AlertSeverity.MODERATE
                current_alerts.append(AlertData(
                    id=str(uuid.uuid4()),
                    type=f"{sensor_name}_low",
                    severity=severity,
                    title=f"Low {sensor_name.replace('_', ' ').title()}",
                    message=f"{sensor_name.replace('_', ' ').title()} is below minimum threshold: {value} < {threshold['min']}",
                    timestamp=datetime.utcnow(),
                    sensor_type=sensor_name,
                    sensor_value=value,
                    threshold_min=threshold['min'],
                    threshold_max=threshold['max']
                ))
            elif value > threshold['max']:
                severity = AlertSeverity.HIGH if value > threshold['max'] * 1.2 else AlertSeverity.MODERATE
                current_alerts.append(AlertData(
                    id=str(uuid.uuid4()),
                    type=f"{sensor_name}_high",
                    severity=severity,
                    title=f"High {sensor_name.replace('_', ' ').title()}",
                    message=f"{sensor_name.replace('_', ' ').title()} is above maximum threshold: {value} > {threshold['max']}",
                    timestamp=datetime.utcnow(),
                    sensor_type=sensor_name,
                    sensor_value=value,
                    threshold_min=threshold['min'],
                    threshold_max=threshold['max']
                ))

        # Update alerts list (keep only recent alerts)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time] + current_alerts

    async def get_active_alerts(self) -> List[AlertData]:
        """Get active system alerts"""
        return [alert for alert in self.alerts if not alert.resolved]

    async def get_irrigation_status(self) -> IrrigationStatus:
        """Get current irrigation system status"""
        return self.irrigation_status

    async def execute_irrigation(self, command: IrrigationCommand):
        """Execute irrigation command"""
        logger.info(f"Executing irrigation command: activate={command.activate}")

        if command.activate:
            self.irrigation_status.is_active = True
            self.irrigation_status.start_time = datetime.utcnow()
            self.irrigation_status.duration_minutes = command.duration_minutes
            self.irrigation_status.remaining_minutes = command.duration_minutes
            self.irrigation_status.current_zone = command.zone_id or "main"
        else:
            self.irrigation_status.is_active = False
            self.irrigation_status.last_activation = self.irrigation_status.start_time
            self.irrigation_status.start_time = None
            self.irrigation_status.duration_minutes = None
            self.irrigation_status.remaining_minutes = None

    async def _alert_monitoring_loop(self):
        """Monitor and manage alerts"""
        while self.monitoring_active:
            try:
                # Clean up old resolved alerts
                cutoff_time = datetime.utcnow() - timedelta(days=7)
                self.alerts = [alert for alert in self.alerts if alert.timestamp > cutoff_time]

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Error in alert monitoring: {e}")
                await asyncio.sleep(30)

    async def _irrigation_management_loop(self):
        """Manage irrigation system timing"""
        while self.monitoring_active:
            try:
                if self.irrigation_status.is_active and self.irrigation_status.remaining_minutes:
                    self.irrigation_status.remaining_minutes -= 1

                    if self.irrigation_status.remaining_minutes <= 0:
                        # Auto-stop irrigation
                        await self.execute_irrigation(IrrigationCommand(activate=False))
                        logger.info("Irrigation automatically stopped - duration completed")

                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in irrigation management: {e}")
                await asyncio.sleep(30)

    async def get_system_health(self) -> str:
        """Get system health status"""
        if self.monitoring_active and self.current_readings:
            return "online"
        return "offline"

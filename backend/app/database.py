"""
Database management for IoT agriculture monitoring system
Uses SQLite for development and PostgreSQL for production
"""

import sqlite3
import aiosqlite
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json
import os

from app.models import SensorReading, NPKReading

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_path = os.getenv("DATABASE_PATH", "agriculture_monitor.db")
        self.db_initialized = False

    async def initialize(self):
        """Initialize database and create tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables(db)
                await db.commit()

            self.db_initialized = True
            logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def _create_tables(self, db):
        """Create database tables"""
        # Sensor readings table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                soil_moisture REAL NOT NULL,
                soil_temperature REAL NOT NULL,
                soil_ph REAL NOT NULL,
                soil_conductivity REAL NOT NULL,
                air_temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                atmospheric_pressure REAL NOT NULL,
                nitrogen REAL NOT NULL,
                phosphorus REAL NOT NULL,
                potassium REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Irrigation events table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS irrigation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                duration_minutes INTEGER,
                zone_id TEXT,
                water_usage_liters REAL,
                trigger_type TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Alerts table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                sensor_type TEXT,
                sensor_value REAL,
                threshold_min REAL,
                threshold_max REAL,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Weather data table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS weather_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                pressure REAL NOT NULL,
                wind_speed REAL NOT NULL,
                wind_direction TEXT NOT NULL,
                description TEXT NOT NULL,
                uv_index INTEGER,
                visibility REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # System events table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT,
                timestamp DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for better performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp ON sensor_readings(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_irrigation_events_start_time ON irrigation_events(start_time)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_weather_data_timestamp ON weather_data(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_system_events_timestamp ON system_events(timestamp)")

    async def store_sensor_reading(self, reading: SensorReading):
        """Store a sensor reading in the database"""
        if not self.db_initialized:
            logger.warning("Database not initialized, skipping sensor reading storage")
            return

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO sensor_readings (
                        timestamp, soil_moisture, soil_temperature, soil_ph, 
                        soil_conductivity, air_temperature, humidity, 
                        atmospheric_pressure, nitrogen, phosphorus, potassium
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    reading.timestamp,
                    reading.soil_moisture,
                    reading.soil_temperature,
                    reading.soil_ph,
                    reading.soil_conductivity,
                    reading.air_temperature,
                    reading.humidity,
                    reading.atmospheric_pressure,
                    reading.npk.nitrogen,
                    reading.npk.phosphorus,
                    reading.npk.potassium
                ))
                await db.commit()

        except Exception as e:
            logger.error(f"Error storing sensor reading: {e}")

    async def get_historical_readings(self, hours: int = 24, sensor_type: Optional[str] = None) -> Dict:
        """Get historical sensor readings"""
        if not self.db_initialized:
            return {"error": "Database not initialized"}

        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)

            async with aiosqlite.connect(self.db_path) as db:
                if sensor_type:
                    # Get specific sensor type data
                    column_map = {
                        'soil_moisture': 'soil_moisture',
                        'soil_temperature': 'soil_temperature', 
                        'soil_ph': 'soil_ph',
                        'soil_conductivity': 'soil_conductivity',
                        'air_temperature': 'air_temperature',
                        'humidity': 'humidity',
                        'atmospheric_pressure': 'atmospheric_pressure',
                        'nitrogen': 'nitrogen',
                        'phosphorus': 'phosphorus',
                        'potassium': 'potassium'
                    }

                    if sensor_type in column_map:
                        column = column_map[sensor_type]
                        cursor = await db.execute(f"""
                            SELECT timestamp, {column} as value
                            FROM sensor_readings 
                            WHERE timestamp >= ?
                            ORDER BY timestamp ASC
                        """, (start_time,))
                    else:
                        return {"error": f"Unknown sensor type: {sensor_type}"}
                else:
                    # Get all sensor data
                    cursor = await db.execute("""
                        SELECT * FROM sensor_readings 
                        WHERE timestamp >= ?
                        ORDER BY timestamp ASC
                    """, (start_time,))

                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]

                # Convert to list of dictionaries
                data_points = []
                for row in rows:
                    data_point = dict(zip(columns, row))
                    # Convert timestamp to ISO format
                    if 'timestamp' in data_point and data_point['timestamp']:
                        if isinstance(data_point['timestamp'], str):
                            data_point['timestamp'] = datetime.fromisoformat(data_point['timestamp']).isoformat()
                        else:
                            data_point['timestamp'] = data_point['timestamp'].isoformat()
                    data_points.append(data_point)

                return {
                    'start_time': start_time.isoformat(),
                    'end_time': datetime.utcnow().isoformat(),
                    'sensor_type': sensor_type,
                    'data_points': data_points,
                    'total_points': len(data_points)
                }

        except Exception as e:
            logger.error(f"Error getting historical readings: {e}")
            return {"error": str(e)}

    async def store_irrigation_event(self, start_time: datetime, end_time: Optional[datetime] = None, 
                                   duration_minutes: Optional[int] = None, zone_id: Optional[str] = None,
                                   water_usage: Optional[float] = None, trigger_type: str = "manual"):
        """Store irrigation event"""
        if not self.db_initialized:
            return

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO irrigation_events (
                        start_time, end_time, duration_minutes, zone_id, 
                        water_usage_liters, trigger_type
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (start_time, end_time, duration_minutes, zone_id, water_usage, trigger_type))
                await db.commit()

        except Exception as e:
            logger.error(f"Error storing irrigation event: {e}")

    async def store_alert(self, alert_id: str, alert_type: str, severity: str, 
                         title: str, message: str, timestamp: datetime,
                         sensor_type: Optional[str] = None, sensor_value: Optional[float] = None,
                         threshold_min: Optional[float] = None, threshold_max: Optional[float] = None):
        """Store system alert"""
        if not self.db_initialized:
            return

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO alerts (
                        id, alert_type, severity, title, message, timestamp,
                        sensor_type, sensor_value, threshold_min, threshold_max
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (alert_id, alert_type, severity, title, message, timestamp,
                     sensor_type, sensor_value, threshold_min, threshold_max))
                await db.commit()

        except Exception as e:
            logger.error(f"Error storing alert: {e}")

    async def store_weather_data(self, weather_data: Dict):
        """Store weather data"""
        if not self.db_initialized:
            return

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO weather_data (
                        timestamp, temperature, humidity, pressure, wind_speed,
                        wind_direction, description, uv_index, visibility
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    weather_data.get('timestamp', datetime.utcnow()),
                    weather_data.get('temperature'),
                    weather_data.get('humidity'),
                    weather_data.get('pressure'),
                    weather_data.get('wind_speed'),
                    weather_data.get('wind_direction'),
                    weather_data.get('description'),
                    weather_data.get('uv_index'),
                    weather_data.get('visibility')
                ))
                await db.commit()

        except Exception as e:
            logger.error(f"Error storing weather data: {e}")

    async def log_system_event(self, event_type: str, event_data: Optional[Dict] = None):
        """Log system event"""
        if not self.db_initialized:
            return

        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO system_events (event_type, event_data, timestamp)
                    VALUES (?, ?, ?)
                """, (event_type, json.dumps(event_data) if event_data else None, datetime.utcnow()))
                await db.commit()

        except Exception as e:
            logger.error(f"Error logging system event: {e}")

    async def get_recent_irrigation_events(self, hours: int = 24) -> List[Dict]:
        """Get recent irrigation events"""
        if not self.db_initialized:
            return []

        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)

            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    SELECT * FROM irrigation_events 
                    WHERE start_time >= ?
                    ORDER BY start_time DESC
                """, (start_time,))

                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]

                events = []
                for row in rows:
                    event = dict(zip(columns, row))
                    # Convert datetime strings to ISO format
                    for date_field in ['start_time', 'end_time', 'created_at']:
                        if event.get(date_field):
                            if isinstance(event[date_field], str):
                                event[date_field] = datetime.fromisoformat(event[date_field]).isoformat()
                            else:
                                event[date_field] = event[date_field].isoformat()
                    events.append(event)

                return events

        except Exception as e:
            logger.error(f"Error getting irrigation events: {e}")
            return []

    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to prevent database from growing too large"""
        if not self.db_initialized:
            return

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            async with aiosqlite.connect(self.db_path) as db:
                # Clean old sensor readings
                await db.execute("DELETE FROM sensor_readings WHERE timestamp < ?", (cutoff_date,))

                # Clean old resolved alerts
                await db.execute("DELETE FROM alerts WHERE resolved = TRUE AND resolved_at < ?", (cutoff_date,))

                # Clean old weather data
                await db.execute("DELETE FROM weather_data WHERE timestamp < ?", (cutoff_date,))

                # Clean old system events
                await db.execute("DELETE FROM system_events WHERE timestamp < ?", (cutoff_date,))

                await db.commit()
                logger.info(f"Cleaned up data older than {days_to_keep} days")

        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")

    async def get_database_stats(self) -> Dict:
        """Get database statistics"""
        if not self.db_initialized:
            return {"error": "Database not initialized"}

        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}

                # Count records in each table
                tables = ['sensor_readings', 'irrigation_events', 'alerts', 'weather_data', 'system_events']

                for table in tables:
                    cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
                    count = await cursor.fetchone()
                    stats[f"{table}_count"] = count[0] if count else 0

                # Get date range of sensor data
                cursor = await db.execute("SELECT MIN(timestamp), MAX(timestamp) FROM sensor_readings")
                date_range = await cursor.fetchone()
                if date_range and date_range[0]:
                    stats['data_start_date'] = date_range[0]
                    stats['data_end_date'] = date_range[1]

                # Database file size
                if os.path.exists(self.db_path):
                    stats['database_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)

                return stats

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {"error": str(e)}

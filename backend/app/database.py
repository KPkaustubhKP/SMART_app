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

        # Create indexes for better performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp ON sensor_readings(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_irrigation_events_start_time ON irrigation_events(start_time)")

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
                cursor = await db.execute("""
                    SELECT * FROM sensor_readings
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                    LIMIT 100
                """, (start_time,))

                rows = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]

                # Convert to list of dictionaries
                data_points = []
                for row in rows:
                    data_point = dict(zip(columns, row))
                    # Convert timestamp to ISO format
                    if 'timestamp' in data_point and data_point['timestamp']:
                        data_point['timestamp'] = data_point['timestamp']
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

    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to prevent database from growing too large"""
        if not self.db_initialized:
            return

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            async with aiosqlite.connect(self.db_path) as db:
                # Clean old sensor readings
                await db.execute("DELETE FROM sensor_readings WHERE timestamp < ?", (cutoff_date,))
                await db.commit()
                logger.info(f"Cleaned up data older than {days_to_keep} days")
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")

"""
Data models for the Smart Agriculture IoT system
Using Pydantic for data validation and serialization
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Union
from enum import Enum

class AlertSeverity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

class SensorType(str, Enum):
    SOIL_MOISTURE = "soil_moisture"
    SOIL_TEMPERATURE = "soil_temperature"
    SOIL_PH = "soil_ph"
    SOIL_CONDUCTIVITY = "soil_conductivity"
    AIR_TEMPERATURE = "air_temperature"
    HUMIDITY = "humidity"
    ATMOSPHERIC_PRESSURE = "atmospheric_pressure"
    NITROGEN = "nitrogen"
    PHOSPHORUS = "phosphorus"
    POTASSIUM = "potassium"

class WeatherAlertType(str, Enum):
    THUNDERSTORM = "thunderstorm"
    HEAVY_RAIN = "heavy_rain"
    DROUGHT = "drought"
    HAIL = "hail"
    HIGH_WINDS = "high_winds"
    FLOOD = "flood"
    FROST = "frost"

class NPKReading(BaseModel):
    nitrogen: float = Field(..., ge=0, le=500, description="Nitrogen level in ppm")
    phosphorus: float = Field(..., ge=0, le=200, description="Phosphorus level in ppm")
    potassium: float = Field(..., ge=0, le=500, description="Potassium level in ppm")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SensorReading(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    soil_moisture: float = Field(..., ge=0, le=100, description="Soil moisture percentage")
    soil_temperature: float = Field(..., ge=-10, le=60, description="Soil temperature in Celsius")
    soil_ph: float = Field(..., ge=3.0, le=14.0, description="Soil pH level")
    soil_conductivity: float = Field(..., ge=0, le=5000, description="Soil conductivity in μS/cm")
    air_temperature: float = Field(..., ge=-50, le=70, description="Air temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Air humidity percentage")
    atmospheric_pressure: float = Field(..., ge=800, le=1200, description="Atmospheric pressure in hPa")
    npk: NPKReading

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class WeatherAlert(BaseModel):
    id: str
    type: WeatherAlertType
    severity: AlertSeverity
    title: str
    message: str
    start_time: datetime
    end_time: Optional[datetime] = None
    affected_areas: List[str] = []

class WeatherData(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    temperature: float = Field(..., description="Current temperature in Celsius")
    humidity: float = Field(..., ge=0, le=100, description="Humidity percentage")
    pressure: float = Field(..., description="Atmospheric pressure in hPa")
    wind_speed: float = Field(..., ge=0, description="Wind speed in km/h")
    wind_direction: str = Field(..., description="Wind direction (N, NE, E, etc.)")
    description: str = Field(..., description="Weather description")
    uv_index: int = Field(..., ge=0, le=11, description="UV index")
    visibility: float = Field(..., ge=0, description="Visibility in km")
    alerts: List[WeatherAlert] = []

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class IrrigationCommand(BaseModel):
    activate: bool = Field(..., description="True to activate, False to deactivate")
    duration_minutes: Optional[int] = Field(None, ge=1, le=180, description="Duration in minutes (if activating)")
    zone_id: Optional[str] = Field(None, description="Specific irrigation zone")

class IrrigationStatus(BaseModel):
    is_active: bool
    current_zone: Optional[str] = None
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    remaining_minutes: Optional[int] = None
    last_activation: Optional[datetime] = None
    total_runtime_today: int = Field(default=0, description="Total runtime in minutes today")
    water_usage_liters: Optional[float] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AlertData(BaseModel):
    id: str
    type: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    sensor_type: Optional[SensorType] = None
    sensor_value: Optional[float] = None
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ThresholdSettings(BaseModel):
    soil_moisture: Dict[str, float] = {"min": 30.0, "max": 70.0}
    soil_temperature: Dict[str, float] = {"min": 15.0, "max": 35.0}
    soil_ph: Dict[str, float] = {"min": 6.0, "max": 7.5}
    air_temperature: Dict[str, float] = {"min": 10.0, "max": 40.0}
    humidity: Dict[str, float] = {"min": 40.0, "max": 80.0}
    npk_nitrogen: Dict[str, float] = {"min": 100.0, "max": 150.0}
    npk_phosphorus: Dict[str, float] = {"min": 30.0, "max": 60.0}
    npk_potassium: Dict[str, float] = {"min": 150.0, "max": 200.0}

class SystemStatus(BaseModel):
    timestamp: datetime
    sensors_online: bool
    weather_service_online: bool
    irrigation_available: bool
    database_connected: bool
    active_alerts: int = 0
    uptime_hours: float = 0.0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

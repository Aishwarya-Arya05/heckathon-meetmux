"""Domain entities – pure data objects independent of API or database layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


# ── Enums ────────────────────────────────────────────────


class LocationType(str, Enum):
    SUPPLIER = "supplier"
    WAREHOUSE = "warehouse"
    DISTRIBUTION_CENTER = "distribution_center"
    SHOP = "shop"
    PORT = "port"


class ShipmentStatus(str, Enum):
    PLANNED = "planned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class PredictionStatus(str, Enum):
    """Distinguishes real model output from fallback estimates."""

    MODEL_PREDICTION = "model_prediction"
    FALLBACK_ESTIMATE = "fallback_estimate"
    UNAVAILABLE = "unavailable"


class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Domain entities ──────────────────────────────────────


@dataclass
class Coordinates:
    lat: float
    lon: float


@dataclass
class Location:
    id: str
    name: str
    type: LocationType
    coordinates: Coordinates
    address: Optional[str] = None
    is_demo_data: bool = False


@dataclass
class Shipment:
    id: str
    origin: Location
    destination: Location
    status: ShipmentStatus
    planned_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    cargo_type: str = ""
    weight_kg: float = 0.0
    is_demo_data: bool = False


@dataclass
class SensorReading:
    id: str
    shipment_id: str
    location_id: str
    timestamp: datetime
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    vibration_g: Optional[float] = None
    alert: bool = False
    alert_reason: str = ""
    is_demo_data: bool = False


@dataclass
class RouteGeometry:
    """GeoJSON-style coordinates [[lon, lat], ...]."""

    coordinates: List[List[float]]


@dataclass
class CandidateRoute:
    id: str
    distance_km: float
    duration_minutes: float
    geometry: RouteGeometry
    provider: str = "mock"  # osrm | mock
    waypoints: List[str] = field(default_factory=list)


@dataclass
class RiskFactor:
    """One explainable contributing factor to a delay-risk estimate."""

    name: str
    description: str
    impact: str  # "increases_risk" | "decreases_risk" | "neutral"
    value: Optional[str] = None  # human-readable value


@dataclass
class DelayRiskEstimate:
    probability: float  # 0.0 – 1.0
    risk_band: RiskBand
    prediction_status: PredictionStatus
    model_version: Optional[str] = None
    factors: List[RiskFactor] = field(default_factory=list)
    message: str = ""  # human-readable status explanation


@dataclass
class SupplyChainLink:
    """A relationship between two supply-chain locations."""

    source: Location
    target: Location
    relationship: str  # supplies | stores | ships_to | follows_route
    active: bool = True

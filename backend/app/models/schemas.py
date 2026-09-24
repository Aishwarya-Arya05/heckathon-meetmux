"""
Pydantic schemas for API requests and responses.

These schemas define the contract between frontend and backend.
All responses use consistent envelope shapes for error handling.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────


class ShipmentStatus(str, Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PredictionStatus(str, Enum):
    """Distinguishes real model output from fallback estimates."""
    MODEL = "model"              # Produced by a trained, versioned model
    FALLBACK = "fallback"        # Rule-based estimate (demo / model unavailable)
    UNAVAILABLE = "unavailable"  # Could not produce any estimate


class LocationType(str, Enum):
    SUPPLIER = "supplier"
    WAREHOUSE = "warehouse"
    DISTRIBUTION_CENTER = "distribution_center"
    SHOP = "shop"
    PORT = "port"


# ── Location ─────────────────────────────────────────────────


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class Location(BaseModel):
    id: str
    name: str
    type: LocationType
    coordinates: Coordinates
    city: Optional[str] = None
    country: Optional[str] = None


# ── Shipment ─────────────────────────────────────────────────


class ShipmentSummary(BaseModel):
    """Lightweight shipment record for list views."""
    id: str
    status: ShipmentStatus
    origin_name: str
    destination_name: str
    planned_delivery: Optional[datetime] = None
    is_demo_data: bool = False


class ShipmentDetail(BaseModel):
    """Full shipment with origin/destination coordinates and linked locations."""
    id: str
    status: ShipmentStatus
    origin: Location
    destination: Location
    planned_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    cargo_type: Optional[str] = None
    weight_kg: Optional[float] = None
    linked_locations: list[Location] = Field(default_factory=list)
    is_demo_data: bool = False


# ── Route ────────────────────────────────────────────────────


class RouteGeometry(BaseModel):
    """GeoJSON-compatible polyline for map rendering."""
    type: str = "LineString"
    coordinates: list[list[float]] = Field(
        ..., description="Array of [lng, lat] pairs"
    )


class RouteRiskEstimate(BaseModel):
    """Risk estimate for a single route, with transparency metadata."""
    probability: float = Field(
        ..., ge=0.0, le=1.0,
        description="Estimated probability of delay (0–1)"
    )
    risk_band: RiskBand
    prediction_status: PredictionStatus
    model_version: Optional[str] = None
    contributing_factors: list[RiskFactor] = Field(default_factory=list)
    explanation: str = Field(
        ...,
        description="Human-readable summary of why this risk level was assigned"
    )


class RiskFactor(BaseModel):
    """One contributing factor to a risk estimate."""
    name: str = Field(..., description="e.g. 'historical_delay_rate'")
    label: str = Field(..., description="Human-readable label")
    value: str = Field(..., description="Display value, e.g. '23%' or '3 alerts'")
    impact: str = Field(
        ..., description="'increases_risk', 'decreases_risk', or 'neutral'"
    )


# Fix forward reference — RouteRiskEstimate references RiskFactor
RouteRiskEstimate.model_rebuild()


class RouteOption(BaseModel):
    """A candidate route between two points."""
    id: str
    name: str = Field(..., description="e.g. 'Route A — via NH48'")
    distance_km: float
    duration_minutes: float
    geometry: RouteGeometry
    risk: Optional[RouteRiskEstimate] = None
    is_fastest: bool = False
    is_shortest: bool = False


# ── API request / response envelopes ─────────────────────────


class RoutePlanRequest(BaseModel):
    """Request body for POST /api/v1/routes/plan."""
    origin_lat: float = Field(..., ge=-90, le=90)
    origin_lng: float = Field(..., ge=-180, le=180)
    destination_lat: float = Field(..., ge=-90, le=90)
    destination_lng: float = Field(..., ge=-180, le=180)
    shipment_id: Optional[str] = None
    alternatives: int = Field(3, ge=1, le=5, description="Max alternative routes")


class PaginatedResponse(BaseModel):
    """Generic paginated list wrapper."""
    items: list = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    has_next: bool


class ErrorResponse(BaseModel):
    """Consistent error shape returned to clients."""
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    services: dict[str, str] = Field(default_factory=dict)


class NetworkResponse(BaseModel):
    """Supply-chain network context for a shipment."""
    shipment_id: str
    locations: list[Location] = Field(default_factory=list)
    connections: list[NetworkConnection] = Field(default_factory=list)
    is_demo_data: bool = False


class NetworkConnection(BaseModel):
    """A relationship between two supply-chain locations."""
    source_id: str
    target_id: str
    relationship: str = Field(..., description="e.g. 'supplies', 'ships_to'")


# Rebuild models with forward references
NetworkResponse.model_rebuild()

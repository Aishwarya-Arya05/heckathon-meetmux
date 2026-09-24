"""Pydantic schemas for API request validation and response serialization."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Shared ───────────────────────────────────────────────


class CoordinatesSchema(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class ErrorResponse(BaseModel):
    """Consistent error envelope – never exposes internals."""

    error: str
    message: str
    request_id: Optional[str] = None


# ── Location ─────────────────────────────────────────────


class LocationResponse(BaseModel):
    id: str
    name: str
    type: str
    coordinates: CoordinatesSchema
    address: Optional[str] = None
    is_demo_data: bool = False


# ── Shipment ─────────────────────────────────────────────


class ShipmentSummary(BaseModel):
    """Lightweight shipment info for list views."""

    id: str
    origin_name: str
    destination_name: str
    status: str
    planned_delivery: Optional[datetime] = None
    cargo_type: str = ""
    is_demo_data: bool = False


class ShipmentDetail(BaseModel):
    id: str
    origin: LocationResponse
    destination: LocationResponse
    status: str
    planned_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    cargo_type: str = ""
    weight_kg: float = 0.0
    is_demo_data: bool = False


class ShipmentListResponse(BaseModel):
    data: List[ShipmentSummary]
    meta: PaginationMeta


# ── Supply-chain network ─────────────────────────────────


class SupplyChainLinkResponse(BaseModel):
    source: LocationResponse
    target: LocationResponse
    relationship: str
    active: bool = True


class ShipmentNetworkResponse(BaseModel):
    shipment_id: str
    locations: List[LocationResponse]
    links: List[SupplyChainLinkResponse]
    is_demo_data: bool = False


# ── Route planning ───────────────────────────────────────


class RoutePlanRequest(BaseModel):
    origin: CoordinatesSchema
    destination: CoordinatesSchema
    shipment_id: Optional[str] = Field(
        None, description="Optional shipment ID for context-aware risk scoring"
    )

    @field_validator("origin", "destination")
    @classmethod
    def coords_not_zero(cls, v: CoordinatesSchema) -> CoordinatesSchema:
        if v.lat == 0.0 and v.lon == 0.0:
            raise ValueError("Coordinates (0, 0) are likely invalid")
        return v


class RiskFactorResponse(BaseModel):
    name: str
    description: str
    impact: str
    value: Optional[str] = None


class DelayRiskResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    probability: float = Field(..., ge=0.0, le=1.0)
    risk_band: str
    prediction_status: str
    model_version: Optional[str] = None
    factors: List[RiskFactorResponse] = []
    message: str = ""


class RouteResponse(BaseModel):
    id: str
    distance_km: float
    duration_minutes: float
    geometry: Dict[str, Any]  # GeoJSON-compatible
    provider: str
    risk: Optional[DelayRiskResponse] = None


class RoutePlanResponse(BaseModel):
    routes: List[RouteResponse]
    origin: CoordinatesSchema
    destination: CoordinatesSchema
    shipment_id: Optional[str] = None
    is_demo_data: bool = False


# ── Health ───────────────────────────────────────────────


class DependencyHealth(BaseModel):
    name: str
    status: str  # "healthy" | "degraded" | "unavailable"
    latency_ms: Optional[float] = None
    message: str = ""


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str
    environment: str
    dependencies: List[DependencyHealth] = []

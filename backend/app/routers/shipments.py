"""Shipment, network, and route-planning endpoints."""

from __future__ import annotations

import logging
import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.dependencies import (
    get_feature_builder,
    get_graph_service,
    get_prediction_service,
    get_route_provider,
)
from app.models.domain import Coordinates
from app.models.schemas import (
    CoordinatesSchema,
    DelayRiskResponse,
    ErrorResponse,
    LocationResponse,
    PaginationMeta,
    RiskFactorResponse,
    RoutePlanRequest,
    RoutePlanResponse,
    RouteResponse,
    ShipmentDetail,
    ShipmentListResponse,
    ShipmentNetworkResponse,
    ShipmentSummary,
    SupplyChainLinkResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shipments", tags=["shipments"])
route_router = APIRouter(prefix="/routes", tags=["routes"])


# ── Helper converters ────────────────────────────────────


def _location_response(loc) -> LocationResponse:
    return LocationResponse(
        id=loc.id,
        name=loc.name,
        type=loc.type.value,
        coordinates=CoordinatesSchema(lat=loc.coordinates.lat, lon=loc.coordinates.lon),
        address=loc.address,
        is_demo_data=loc.is_demo_data,
    )


# ── Shipment endpoints ──────────────────────────────────


@router.get(
    "",
    response_model=ShipmentListResponse,
    responses={500: {"model": ErrorResponse}},
    summary="List shipments",
    description="Paginated list of shipments with optional status filter.",
)
async def list_shipments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    graph = get_graph_service()
    try:
        shipments, total = await graph.get_shipments(page, page_size, status)
    except Exception as exc:
        logger.error("Failed to fetch shipments: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Supply chain database is temporarily unavailable",
        )

    total_pages = max(1, math.ceil(total / page_size))

    return ShipmentListResponse(
        data=[
            ShipmentSummary(
                id=s.id,
                origin_name=s.origin.name,
                destination_name=s.destination.name,
                status=s.status.value,
                planned_delivery=s.planned_delivery,
                cargo_type=s.cargo_type,
                is_demo_data=s.is_demo_data,
            )
            for s in shipments
        ],
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total,
            total_pages=total_pages,
        ),
    )


@router.get(
    "/{shipment_id}",
    response_model=ShipmentDetail,
    responses={404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Get shipment details",
)
async def get_shipment(shipment_id: str):
    graph = get_graph_service()
    try:
        shipment = await graph.get_shipment(shipment_id)
    except Exception as exc:
        logger.error("Failed to fetch shipment %s: %s", shipment_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Supply chain database is temporarily unavailable",
        )

    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    return ShipmentDetail(
        id=shipment.id,
        origin=_location_response(shipment.origin),
        destination=_location_response(shipment.destination),
        status=shipment.status.value,
        planned_delivery=shipment.planned_delivery,
        actual_delivery=shipment.actual_delivery,
        cargo_type=shipment.cargo_type,
        weight_kg=shipment.weight_kg,
        is_demo_data=shipment.is_demo_data,
    )


@router.get(
    "/{shipment_id}/network",
    response_model=ShipmentNetworkResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get shipment supply-chain network",
    description="Returns connected locations and relationships for a shipment.",
)
async def get_shipment_network(shipment_id: str):
    graph = get_graph_service()

    shipment = await graph.get_shipment(shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    try:
        locations, links = await graph.get_shipment_network(shipment_id)
    except Exception as exc:
        logger.error("Failed to fetch network for %s: %s", shipment_id, exc)
        raise HTTPException(
            status_code=503,
            detail="Supply chain database is temporarily unavailable",
        )

    return ShipmentNetworkResponse(
        shipment_id=shipment_id,
        locations=[_location_response(loc) for loc in locations],
        links=[
            SupplyChainLinkResponse(
                source=_location_response(link.source),
                target=_location_response(link.target),
                relationship=link.relationship,
                active=link.active,
            )
            for link in links
        ],
        is_demo_data=shipment.is_demo_data,
    )


# ── Route planning ──────────────────────────────────────


@route_router.post(
    "/plan",
    response_model=RoutePlanResponse,
    responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
    summary="Plan routes between two points",
    description=(
        "Returns candidate routes with delay-risk estimates. "
        "Optionally provide a shipment_id for context-aware scoring."
    ),
)
async def plan_routes(request: RoutePlanRequest):
    route_provider = get_route_provider()
    graph = get_graph_service()
    feature_builder = get_feature_builder()
    prediction_service = get_prediction_service()

    origin = Coordinates(lat=request.origin.lat, lon=request.origin.lon)
    destination = Coordinates(lat=request.destination.lat, lon=request.destination.lon)

    # ── Fetch routes ─────────────────────────
    try:
        candidate_routes = await route_provider.get_routes(origin, destination)
    except Exception as exc:
        logger.error("Route provider failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Routing service is temporarily unavailable",
        )

    if not candidate_routes:
        return RoutePlanResponse(
            routes=[],
            origin=request.origin,
            destination=request.destination,
            shipment_id=request.shipment_id,
            is_demo_data=True,
        )

    # ── Get shipment context if provided ─────
    shipment = None
    sensors = []
    links = []
    is_demo = True

    if request.shipment_id:
        shipment = await graph.get_shipment(request.shipment_id)
        if shipment:
            is_demo = shipment.is_demo_data
            sensors = await graph.get_sensor_readings(request.shipment_id)
            _, links = await graph.get_shipment_network(request.shipment_id)

    # ── Score each route ─────────────────────
    route_responses: list[RouteResponse] = []

    for route in candidate_routes:
        features = feature_builder.build_features(
            route=route,
            shipment=shipment,
            sensors=sensors,
            links=links,
            origin_id=request.shipment_id or "",
            destination_id="",
        )

        risk_estimate = prediction_service.predict(features)

        route_responses.append(
            RouteResponse(
                id=route.id,
                distance_km=route.distance_km,
                duration_minutes=route.duration_minutes,
                geometry={
                    "type": "LineString",
                    "coordinates": route.geometry.coordinates,
                },
                provider=route.provider,
                risk=DelayRiskResponse(
                    probability=risk_estimate.probability,
                    risk_band=risk_estimate.risk_band.value,
                    prediction_status=risk_estimate.prediction_status.value,
                    model_version=risk_estimate.model_version,
                    factors=[
                        RiskFactorResponse(
                            name=f.name,
                            description=f.description,
                            impact=f.impact,
                            value=f.value,
                        )
                        for f in risk_estimate.factors
                    ],
                    message=risk_estimate.message,
                ),
            )
        )

    return RoutePlanResponse(
        routes=route_responses,
        origin=request.origin,
        destination=request.destination,
        shipment_id=request.shipment_id,
        is_demo_data=is_demo,
    )

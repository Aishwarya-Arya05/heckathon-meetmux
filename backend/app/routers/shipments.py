"""
Shipment and route planning endpoints.

- GET  /api/v1/shipments           — list shipments (paginated)
- GET  /api/v1/shipments/{id}      — shipment detail with linked locations
- GET  /api/v1/shipments/{id}/network — supply-chain network context
- POST /api/v1/routes/plan         — plan routes with risk estimates
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import (
    get_feature_builder,
    get_graph_service,
    get_prediction_service,
    get_route_service,
)
from app.models.schemas import (
    Coordinates,
    ErrorResponse,
    NetworkConnection,
    NetworkResponse,
    PaginatedResponse,
    RoutePlanRequest,
    RouteOption,
    ShipmentDetail,
    ShipmentSummary,
)
from app.services.feature_builder import FeatureBuilder
from app.services.graph_service import GraphServiceBase
from app.services.prediction_service import PredictionServiceBase
from app.services.route_service import RouteServiceBase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["shipments"])


# ── Shipment endpoints ───────────────────────────────────────


@router.get(
    "/shipments",
    response_model=PaginatedResponse,
    responses={500: {"model": ErrorResponse}},
)
async def list_shipments(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    graph: GraphServiceBase = Depends(get_graph_service),
):
    """List all shipments with pagination."""
    try:
        shipments, total = await graph.list_shipments(page=page, page_size=page_size)
        return PaginatedResponse(
            items=[s.model_dump() for s in shipments],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size < total),
        )
    except Exception:
        logger.exception("Failed to list shipments")
        raise HTTPException(status_code=500, detail="Failed to retrieve shipments")


@router.get(
    "/shipments/{shipment_id}",
    response_model=ShipmentDetail,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def get_shipment(
    shipment_id: str,
    graph: GraphServiceBase = Depends(get_graph_service),
):
    """Get shipment details including origin, destination, and linked locations."""
    try:
        shipment = await graph.get_shipment(shipment_id)
    except Exception:
        logger.exception("Failed to get shipment %s", shipment_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve shipment")

    if not shipment:
        raise HTTPException(status_code=404, detail=f"Shipment '{shipment_id}' not found")

    return shipment


@router.get(
    "/shipments/{shipment_id}/network",
    response_model=NetworkResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_shipment_network(
    shipment_id: str,
    graph: GraphServiceBase = Depends(get_graph_service),
):
    """Get the supply-chain network context for a shipment."""
    try:
        locations, connections = await graph.get_shipment_network(shipment_id)
    except Exception:
        logger.exception("Failed to get network for shipment %s", shipment_id)
        raise HTTPException(status_code=500, detail="Failed to retrieve shipment network")

    if not locations:
        raise HTTPException(
            status_code=404,
            detail=f"No network data found for shipment '{shipment_id}'",
        )

    return NetworkResponse(
        shipment_id=shipment_id,
        locations=locations,
        connections=connections,
        is_demo_data=True,  # Updated by graph service in production
    )


# ── Route planning ───────────────────────────────────────────


@router.post(
    "/routes/plan",
    response_model=list[RouteOption],
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def plan_routes(
    request: RoutePlanRequest,
    route_service: RouteServiceBase = Depends(get_route_service),
    prediction_service: PredictionServiceBase = Depends(get_prediction_service),
    feature_builder: FeatureBuilder = Depends(get_feature_builder),
    graph: GraphServiceBase = Depends(get_graph_service),
):
    """
    Plan routes between origin and destination, with delay risk estimates.

    If a shipment_id is provided, the system retrieves shipment context
    (linked locations, cargo type, historical data) for richer risk analysis.
    """
    origin = Coordinates(lat=request.origin_lat, lng=request.origin_lng)
    destination = Coordinates(lat=request.destination_lat, lng=request.destination_lng)

    # Optionally load shipment context
    shipment: Optional[ShipmentDetail] = None
    if request.shipment_id:
        try:
            shipment = await graph.get_shipment(request.shipment_id)
        except Exception:
            logger.warning("Could not load shipment %s for route planning", request.shipment_id)

    # Get candidate routes
    try:
        routes = await route_service.get_routes(origin, destination, request.alternatives)
    except Exception:
        logger.exception("Route service failed")
        raise HTTPException(status_code=502, detail="Routing service unavailable")

    if not routes:
        logger.warning("No routes found between (%s,%s) and (%s,%s)",
                        origin.lat, origin.lng, destination.lat, destination.lng)
        return []

    # Add risk estimates to each route
    for route in routes:
        try:
            features = feature_builder.build_features(
                route=route,
                shipment=shipment,
                origin=origin,
                destination=destination,
            )
            risk = await prediction_service.predict(features, route, shipment)
            route.risk = risk
        except Exception:
            logger.exception("Risk estimation failed for route %s", route.id)
            # Route is still usable without risk estimate

    return routes

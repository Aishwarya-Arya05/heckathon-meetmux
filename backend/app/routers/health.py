"""
Health check endpoints.

Provides:
- /api/v1/health — application-level health (always responds if the app is up)
- /api/v1/health/ready — readiness check (reports dependency status)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.dependencies import get_graph_service, get_route_service, get_prediction_service
from app.models.schemas import HealthResponse
from app.services.graph_service import GraphServiceBase
from app.services.prediction_service import PredictionServiceBase, PredictionStatus
from app.services.route_service import RouteServiceBase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health():
    """Application liveness check — returns OK if the process is running."""
    return HealthResponse(status="ok", version="0.1.0")


@router.get("/ready", response_model=HealthResponse)
async def readiness(
    graph: GraphServiceBase = Depends(get_graph_service),
    routes: RouteServiceBase = Depends(get_route_service),
    prediction: PredictionServiceBase = Depends(get_prediction_service),
):
    """
    Readiness check — reports status of each dependency.
    Returns 200 even if dependencies are degraded (frontend needs to know status).
    """
    services: dict[str, str] = {}

    # Graph DB
    try:
        graph_ok = await graph.health_check()
        services["graph_database"] = "connected" if graph_ok else "degraded"
    except Exception:
        services["graph_database"] = "unavailable"

    # Routing
    try:
        route_ok = await routes.health_check()
        services["routing"] = "connected" if route_ok else "degraded"
    except Exception:
        services["routing"] = "unavailable"

    # Prediction
    pred_type = prediction.get_prediction_status_type()
    if pred_type == PredictionStatus.MODEL:
        services["prediction"] = f"model_v{prediction.get_model_version()}"
    elif pred_type == PredictionStatus.FALLBACK:
        services["prediction"] = "fallback (demo)"
    else:
        services["prediction"] = "unavailable"

    overall = "ok" if all(v not in ("unavailable",) for v in services.values()) else "degraded"

    return HealthResponse(status=overall, version="0.1.0", services=services)

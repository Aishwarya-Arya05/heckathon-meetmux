"""Health and readiness check endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter

from app.dependencies import get_graph_service, get_prediction_service, get_route_provider
from app.models.schemas import DependencyHealth, HealthResponse

router = APIRouter(tags=["health"])

APP_VERSION = "0.1.0"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Application health – checks all downstream dependencies."""
    deps: list[DependencyHealth] = []
    overall = "healthy"

    # ── Neo4j / Graph ────────────────────────
    graph = get_graph_service()
    start = time.monotonic()
    try:
        ok, msg = await graph.health_check()
        latency = (time.monotonic() - start) * 1000
        deps.append(
            DependencyHealth(
                name="graph_database",
                status="healthy" if ok else "degraded",
                latency_ms=round(latency, 1),
                message=msg,
            )
        )
        if not ok:
            overall = "degraded"
    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        deps.append(
            DependencyHealth(
                name="graph_database",
                status="unavailable",
                latency_ms=round(latency, 1),
                message=str(exc)[:100],
            )
        )
        overall = "degraded"

    # ── Route provider ───────────────────────
    route_provider = get_route_provider()
    start = time.monotonic()
    try:
        ok, msg = await route_provider.health_check()
        latency = (time.monotonic() - start) * 1000
        deps.append(
            DependencyHealth(
                name="route_provider",
                status="healthy" if ok else "degraded",
                latency_ms=round(latency, 1),
                message=msg,
            )
        )
    except Exception:
        latency = (time.monotonic() - start) * 1000
        deps.append(
            DependencyHealth(
                name="route_provider",
                status="unavailable",
                latency_ms=round(latency, 1),
            )
        )

    # ── Prediction service ───────────────────
    pred = get_prediction_service()
    deps.append(
        DependencyHealth(
            name="prediction_model",
            status="healthy" if pred.is_model_loaded() else "degraded",
            message=(
                f"model v{pred.model_version()}"
                if pred.is_model_loaded()
                else "no trained model – using fallback estimator"
            ),
        )
    )

    from app.config import settings

    return HealthResponse(
        status=overall,
        version=APP_VERSION,
        environment=settings.app_env,
        dependencies=deps,
    )

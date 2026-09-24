"""
FastAPI application entry point.

Configures middleware, lifespan events, and mounts routers.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import health, shipments
from app.services.feature_builder import FeatureBuilder
from app.services.graph_service import create_graph_service
from app.services.prediction_service import create_prediction_service
from app.services.route_service import create_route_service

# ── Logging ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan — service initialisation & teardown ─────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise services on startup, clean up on shutdown."""
    settings = get_settings()
    logger.info("Starting application in %s mode", settings.app_env)

    # Create services
    app.state.graph_service = await create_graph_service(
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password,
        neo4j_database=settings.neo4j_database,
    )

    app.state.route_service = create_route_service(
        provider=settings.routing_provider,
        osrm_base_url=settings.osrm_base_url,
        osrm_timeout=settings.osrm_timeout_seconds,
    )

    app.state.prediction_service = create_prediction_service(
        model_path=settings.model_path,
        model_version=settings.model_version,
    )

    app.state.feature_builder = FeatureBuilder()

    logger.info(
        "Services ready — graph=%s, routing=%s, prediction=%s",
        type(app.state.graph_service).__name__,
        type(app.state.route_service).__name__,
        type(app.state.prediction_service).__name__,
    )

    yield

    # Cleanup
    if hasattr(app.state.graph_service, "close"):
        await app.state.graph_service.close()
    if hasattr(app.state.route_service, "close"):
        await app.state.route_service.close()

    logger.info("Application shutdown complete")


# ── App factory ──────────────────────────────────────────────


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Supply Chain Delay Risk & Route Planning API",
        description=(
            "API for supply-chain operators to inspect shipments, "
            "compare road routes, and review estimated delay risk."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ── Request ID & logging middleware ──────────────────────
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
        start_time = time.time()

        # Store request ID for downstream use
        request.state.request_id = request_id

        try:
            response: Response = await call_next(request)
        except Exception:
            logger.exception("Unhandled error [request_id=%s]", request_id)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                },
            )

        duration_ms = (time.time() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "%s %s %d %.1fms [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )

        return response

    # ── Routers ──────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(shipments.router)

    return app


# Module-level app instance for uvicorn
app = create_app()

"""
FastAPI application entry point.

Initializes services, attaches middleware and routers,
and configures structured logging.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load .env before importing config
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.dependencies import init_services, shutdown_services
from app.middleware import setup_middleware
from app.routers.health import router as health_router
from app.routers.shipments import route_router, router as shipments_router


# ── Logging setup ────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ── Application lifecycle ────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    logger.info("Starting Supply Chain Delay Risk API (env=%s)", settings.app_env)
    await init_services()
    logger.info("All services initialized")
    yield
    logger.info("Shutting down...")
    await shutdown_services()


# ── Application factory ──────────────────────────────────

app = FastAPI(
    title="Supply Chain Shipment Delay Risk API",
    description=(
        "API for supply-chain shipment tracking, route planning, "
        "and delay-risk estimation with transparent contributing factors."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# ── Middleware ────────────────────────────────────────────
setup_middleware(app)

# ── Routers ──────────────────────────────────────────────
app.include_router(health_router, prefix="/api/v1")
app.include_router(shipments_router, prefix="/api/v1")
app.include_router(route_router, prefix="/api/v1")


# ── Root redirect ────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Supply Chain Delay Risk API", "docs": "/docs", "health": "/api/v1/health"}


# ── Global exception handler ────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception | request_id=%s error=%s",
        request_id,
        type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred.",
            "request_id": request_id,
        },
    )

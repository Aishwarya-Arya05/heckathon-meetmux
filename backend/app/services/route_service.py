"""
Route service — fetches candidate road routes between two points.

Production: Calls a self-hosted or licensed OSRM instance.
Demo: Returns synthetic routes based on straight-line distance.

The provider is selected by configuration. The public OSRM demo server
is NOT used as a production endpoint (it has no SLA and rate-limits).
"""

from __future__ import annotations

import logging
import math
import uuid
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from app.models.schemas import Coordinates, RouteGeometry, RouteOption

logger = logging.getLogger(__name__)


# ── Abstract interface ───────────────────────────────────────


class RouteServiceBase(ABC):
    """Interface for route providers."""

    @abstractmethod
    async def get_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        alternatives: int = 3,
    ) -> list[RouteOption]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...


# ── OSRM implementation ─────────────────────────────────────


class OSRMRouteService(RouteServiceBase):
    """
    Fetches routes from a configured OSRM instance.
    This should be a self-hosted or licensed OSRM server,
    NOT the public demo at router.project-osrm.org.
    """

    def __init__(self, base_url: str, timeout_seconds: int = 10):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = httpx.AsyncClient(timeout=self._timeout)

    async def close(self):
        await self._client.aclose()

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/health", timeout=5)
            return resp.status_code == 200
        except Exception:
            # Try a simple route request as health check
            try:
                resp = await self._client.get(
                    f"{self._base_url}/route/v1/driving/77.1025,28.7041;72.8777,19.076",
                    params={"overview": "false"},
                    timeout=5,
                )
                return resp.status_code == 200
            except Exception:
                return False

    async def get_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        alternatives: int = 3,
    ) -> list[RouteOption]:
        coords = f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"
        url = f"{self._base_url}/route/v1/driving/{coords}"
        params = {
            "alternatives": str(min(alternatives, 3)),
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        }

        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.TimeoutException:
            logger.error("OSRM request timed out after %ds", self._timeout)
            return []
        except httpx.HTTPStatusError as e:
            logger.error("OSRM returned HTTP %d: %s", e.response.status_code, e.response.text[:200])
            return []
        except Exception:
            logger.exception("OSRM request failed")
            return []

        if data.get("code") != "Ok" or not data.get("routes"):
            logger.warning("OSRM returned no routes: %s", data.get("code"))
            return []

        routes = []
        for i, route in enumerate(data["routes"]):
            distance_km = route["distance"] / 1000.0
            duration_min = route["duration"] / 60.0
            geometry = route.get("geometry", {})

            route_option = RouteOption(
                id=f"route-{uuid.uuid4().hex[:8]}",
                name=f"Route {chr(65 + i)}",
                distance_km=round(distance_km, 1),
                duration_minutes=round(duration_min, 1),
                geometry=RouteGeometry(
                    type="LineString",
                    coordinates=geometry.get("coordinates", []),
                ),
                is_fastest=(i == 0),
                is_shortest=(
                    distance_km == min(r["distance"] / 1000.0 for r in data["routes"])
                ),
            )
            routes.append(route_option)

        return routes


# ── Demo fallback ────────────────────────────────────────────


class DemoRouteService(RouteServiceBase):
    """
    Returns synthetic routes based on straight-line distance.
    These are illustrative and NOT real road routes.
    """

    async def health_check(self) -> bool:
        return True

    async def get_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        alternatives: int = 3,
    ) -> list[RouteOption]:
        straight_km = _haversine_km(origin, destination)
        routes = []

        # Generate plausible alternative routes with varying factors
        variations = [
            ("Route A — Direct", 1.15, 55),   # +15% vs straight line
            ("Route B — Highway", 1.25, 50),   # Longer but faster
            ("Route C — Scenic", 1.40, 45),    # Longest, slowest
        ]

        for i, (name, dist_factor, speed_kmh) in enumerate(variations[:alternatives]):
            route_km = round(straight_km * dist_factor, 1)
            duration_min = round((route_km / speed_kmh) * 60, 1)

            # Generate a synthetic polyline (straight line with slight curve)
            coords = _generate_demo_polyline(origin, destination, curve_factor=i * 0.02)

            routes.append(
                RouteOption(
                    id=f"demo-route-{chr(97 + i)}",
                    name=name,
                    distance_km=route_km,
                    duration_minutes=duration_min,
                    geometry=RouteGeometry(type="LineString", coordinates=coords),
                    is_fastest=(i == 1),  # Highway is fastest
                    is_shortest=(i == 0),  # Direct is shortest
                )
            )

        return routes


# ── Helpers ──────────────────────────────────────────────────


def _haversine_km(a: Coordinates, b: Coordinates) -> float:
    """Calculate great-circle distance between two points."""
    R = 6371  # Earth radius in km
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = math.radians(b.lat - a.lat)
    dlng = math.radians(b.lng - a.lng)
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(h))


def _generate_demo_polyline(
    origin: Coordinates, destination: Coordinates, curve_factor: float = 0.0, points: int = 20
) -> list[list[float]]:
    """Generate a synthetic polyline with a slight curve for visual variety."""
    coords = []
    for i in range(points + 1):
        t = i / points
        # Linear interpolation with a perpendicular offset for curvature
        lat = origin.lat + (destination.lat - origin.lat) * t
        lng = origin.lng + (destination.lng - origin.lng) * t

        # Add perpendicular curve
        if curve_factor != 0:
            perp_offset = curve_factor * math.sin(t * math.pi)
            lat += perp_offset * (destination.lng - origin.lng)
            lng -= perp_offset * (destination.lat - origin.lat)

        coords.append([round(lng, 6), round(lat, 6)])

    return coords


# ── Factory ──────────────────────────────────────────────────


def create_route_service(
    provider: str = "demo",
    osrm_base_url: Optional[str] = None,
    osrm_timeout: int = 10,
) -> RouteServiceBase:
    if provider == "osrm" and osrm_base_url:
        logger.info("Using OSRM route service at %s", osrm_base_url)
        return OSRMRouteService(osrm_base_url, osrm_timeout)
    else:
        logger.info("Using demo route service (synthetic routes)")
        return DemoRouteService()

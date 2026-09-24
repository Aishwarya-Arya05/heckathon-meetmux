"""
Route service – isolates routing behind a provider interface.

Supports:
  - MockRouteProvider: generates plausible routes from coordinates (demo mode)
  - OSRMRouteProvider: calls a self-hosted or configured OSRM instance
"""

from __future__ import annotations

import logging
import math
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from app.models.domain import CandidateRoute, Coordinates, RouteGeometry

logger = logging.getLogger(__name__)


# ── Abstract interface ───────────────────────────────────


class RouteProviderBase(ABC):
    """Interface for route computation providers."""

    @abstractmethod
    async def get_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        alternatives: int = 3,
    ) -> List[CandidateRoute]:
        """Return candidate routes between two points."""

    @abstractmethod
    async def health_check(self) -> tuple[bool, str]:
        """Return (is_healthy, message)."""


# ── OSRM implementation ─────────────────────────────────


class OSRMRouteProvider(RouteProviderBase):
    """Calls a configured OSRM instance (self-hosted or public demo).

    Public demo: http://router.project-osrm.org
    Self-hosted: configured via OSRM_BASE_URL

    WARNING: The public OSRM demo server has no SLA and should not be
    used for production. Set ROUTE_PROVIDER=osrm_self_hosted with your
    own OSRM instance for production use.
    """

    def __init__(self, base_url: str, timeout_seconds: int = 10):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def get_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        alternatives: int = 3,
    ) -> List[CandidateRoute]:
        coords = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
        url = (
            f"{self._base_url}/route/v1/driving/{coords}"
            f"?overview=full&geometries=geojson&alternatives={'true' if alternatives > 1 else 'false'}"
        )

        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException:
            logger.warning("OSRM request timed out after %ds", self._timeout)
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning("OSRM returned HTTP %d: %s", exc.response.status_code, exc)
            return []
        except Exception as exc:
            logger.error("OSRM request failed: %s", exc)
            return []

        if data.get("code") != "Ok":
            logger.warning("OSRM response code: %s", data.get("code"))
            return []

        routes: List[CandidateRoute] = []
        for i, route_data in enumerate(data.get("routes", [])):
            geometry = route_data.get("geometry", {})
            coords_list = geometry.get("coordinates", [])

            routes.append(
                CandidateRoute(
                    id=f"route-{i + 1}",
                    distance_km=round(route_data["distance"] / 1000, 2),
                    duration_minutes=round(route_data["duration"] / 60, 1),
                    geometry=RouteGeometry(coordinates=coords_list),
                    provider="osrm",
                )
            )

        return routes[:alternatives]

    async def health_check(self) -> tuple[bool, str]:
        try:
            resp = await self._client.get(f"{self._base_url}/health", timeout=5)
            if resp.status_code < 500:
                return True, "osrm reachable"
            return False, f"osrm returned {resp.status_code}"
        except Exception as exc:
            return False, f"osrm unreachable: {exc}"

    async def close(self):
        await self._client.aclose()


# ── Mock implementation (demo mode) ─────────────────────


class MockRouteProvider(RouteProviderBase):
    """Generates plausible mock routes for demo mode.

    Creates 2-3 routes with realistic distances based on
    great-circle distance, with slight variations.
    """

    async def get_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        alternatives: int = 3,
    ) -> List[CandidateRoute]:
        base_distance = self._haversine_km(origin, destination)
        if base_distance < 1:
            return []

        routes: List[CandidateRoute] = []
        route_count = min(alternatives, 3)

        # Generate route variations
        multipliers = [1.0, 1.15, 1.30][:route_count]
        speed_kmh = [55, 50, 45][:route_count]
        labels = ["Fastest route", "Alternative via highway", "Scenic / longer route"]

        for i, (mult, speed) in enumerate(zip(multipliers, speed_kmh)):
            distance = round(base_distance * mult, 2)
            duration = round((distance / speed) * 60, 1)

            # Generate a simple polyline (straight line with slight curve)
            geometry = self._generate_mock_geometry(origin, destination, curve_factor=i * 0.02)

            routes.append(
                CandidateRoute(
                    id=f"mock-route-{i + 1}",
                    distance_km=distance,
                    duration_minutes=duration,
                    geometry=RouteGeometry(coordinates=geometry),
                    provider="mock",
                    waypoints=[labels[i]],
                )
            )

        return routes

    async def health_check(self) -> tuple[bool, str]:
        return True, "mock provider always available"

    @staticmethod
    def _haversine_km(a: Coordinates, b: Coordinates) -> float:
        R = 6371.0
        lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
        dlat = math.radians(b.lat - a.lat)
        dlon = math.radians(b.lon - a.lon)
        h = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        return R * 2 * math.asin(math.sqrt(h))

    @staticmethod
    def _generate_mock_geometry(
        origin: Coordinates,
        destination: Coordinates,
        curve_factor: float = 0.0,
        num_points: int = 20,
    ) -> List[List[float]]:
        """Generate a curved polyline between two points."""
        coords = []
        for i in range(num_points + 1):
            t = i / num_points
            lat = origin.lat + t * (destination.lat - origin.lat)
            lon = origin.lon + t * (destination.lon - origin.lon)
            # Add a slight curve
            offset = curve_factor * math.sin(math.pi * t)
            lat += offset
            lon += offset * 0.5
            coords.append([round(lon, 6), round(lat, 6)])
        return coords


# ── Factory ──────────────────────────────────────────────


def create_route_provider(
    provider_type: str,
    osrm_base_url: str = "",
    timeout_seconds: int = 10,
) -> RouteProviderBase:
    """Factory to create the configured route provider."""
    if provider_type == "osrm_self_hosted":
        if not osrm_base_url:
            logger.warning("OSRM_BASE_URL not set, falling back to mock provider")
            return MockRouteProvider()
        return OSRMRouteProvider(osrm_base_url, timeout_seconds)

    if provider_type == "osrm_public_demo":
        logger.warning(
            "Using public OSRM demo server – NOT suitable for production. "
            "Set ROUTE_PROVIDER=osrm_self_hosted with your own instance."
        )
        return OSRMRouteProvider("http://router.project-osrm.org", timeout_seconds)

    return MockRouteProvider()

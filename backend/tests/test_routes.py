"""Tests for route planning and validation endpoints."""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_plan_route_valid_coordinates():
    payload = {
        "origin": {"lat": 18.5204, "lon": 73.8567},
        "destination": {"lat": 19.0760, "lon": 72.8777},
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/routes/plan", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "routes" in data
    assert len(data["routes"]) >= 1
    
    route = data["routes"][0]
    assert "id" in route
    assert "distance_km" in route
    assert route["distance_km"] > 0
    assert "duration_minutes" in route
    assert route["duration_minutes"] > 0
    assert "geometry" in route
    assert "coordinates" in route["geometry"]
    assert "risk" in route
    assert route["risk"] is not None
    assert "risk_band" in route["risk"]
    assert "prediction_status" in route["risk"]
    assert "factors" in route["risk"]


@pytest.mark.asyncio
async def test_plan_route_invalid_coordinates():
    # Latitude out of bounds (> 90)
    payload = {
        "origin": {"lat": 99.0, "lon": 73.8567},
        "destination": {"lat": 19.0760, "lon": 72.8777},
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/routes/plan", json=payload)
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_plan_route_missing_fields():
    payload = {
        "origin": {"lat": 18.5204},
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/routes/plan", json=payload)
    
    assert response.status_code == 422

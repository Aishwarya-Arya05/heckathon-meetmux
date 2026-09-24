"""Tests for application health and readiness checks."""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_check_returns_valid_structure():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data
    assert "environment" in data
    assert "dependencies" in data
    assert isinstance(data["dependencies"], list)
    
    # Must report key downstream dependencies
    dep_names = [d["name"] for d in data["dependencies"]]
    assert "graph_database" in dep_names
    assert "route_provider" in dep_names
    assert "prediction_model" in dep_names


@pytest.mark.asyncio
async def test_request_id_header_present():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/health")
    
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0

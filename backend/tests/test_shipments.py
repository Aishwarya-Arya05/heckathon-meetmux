"""Tests for shipment listing, details, and network context endpoints."""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_get_shipments_list_pagination():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/shipments?page=1&page_size=5")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    assert "meta" in data
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 5
    assert len(data["data"]) <= 5
    assert data["meta"]["total_items"] >= 0
    
    if len(data["data"]) > 0:
        item = data["data"][0]
        assert "id" in item
        assert "origin_name" in item
        assert "destination_name" in item
        assert "status" in item
        assert "cargo_type" in item
        assert "is_demo_data" in item


@pytest.mark.asyncio
async def test_get_shipments_filter_by_status():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/shipments?status=in_transit")
    
    assert response.status_code == 200
    data = response.json()
    for item in data["data"]:
        assert item["status"] == "in_transit"


@pytest.mark.asyncio
async def test_get_shipment_by_id_found():
    # First get a valid ID from the list
    async with AsyncClient(app=app, base_url="http://test") as ac:
        list_res = await ac.get("/api/v1/shipments?page=1&page_size=1")
        assert list_res.status_code == 200
        items = list_res.json()["data"]
        if not items:
            pytest.skip("No shipments seeded in environment")
        
        valid_id = items[0]["id"]
        detail_res = await ac.get(f"/api/v1/shipments/{valid_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == valid_id
        assert "origin" in detail
        assert "destination" in detail
        assert "coordinates" in detail["origin"]
        assert "coordinates" in detail["destination"]


@pytest.mark.asyncio
async def test_get_shipment_by_id_not_found():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/v1/shipments/SHP-NONEXISTENT-999")
    
    assert response.status_code == 404
    err = response.json()
    assert "error" in err or "message" in err or "detail" in err


@pytest.mark.asyncio
async def test_get_shipment_network():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        list_res = await ac.get("/api/v1/shipments?page=1&page_size=1")
        items = list_res.json()["data"]
        if not items:
            pytest.skip("No shipments seeded")
        
        shipment_id = items[0]["id"]
        net_res = await ac.get(f"/api/v1/shipments/{shipment_id}/network")
        assert net_res.status_code == 200
        net_data = net_res.json()
        assert "shipment_id" in net_data
        assert "locations" in net_data
        assert "links" in net_data
        assert "is_demo_data" in net_data

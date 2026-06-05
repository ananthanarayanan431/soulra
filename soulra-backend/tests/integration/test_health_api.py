import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_status_returns_components(client):
    resp = await client.get("/api/v1/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "database" in data["data"]
    assert "vector_store" in data["data"]


@pytest.mark.asyncio
async def test_404_returns_not_found_code(client):
    """HTTP 404 must return code NOT_FOUND, not HTTP_ERROR."""
    resp = await client.get("/api/v1/conversations/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND", \
        f"Expected NOT_FOUND, got {body['error']['code']}"


@pytest.mark.asyncio
async def test_validation_error_returns_validation_error_code(client):
    """Pydantic validation failures must return code VALIDATION_ERROR."""
    # Pass invalid UUID to trigger FastAPI validation
    resp = await client.get("/api/v1/conversations/not-a-uuid")
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "VALIDATION_ERROR", \
        f"Expected VALIDATION_ERROR, got {body['error']['code']}"

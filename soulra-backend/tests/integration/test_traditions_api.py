import pytest
from soulra.models.tradition import Tradition


@pytest.mark.asyncio
async def test_get_tradition_returns_detail_with_description(client, test_db):
    row = Tradition(
        slug="zen",
        name="Zen",
        origin="Japan · ~1200 CE",
        era="medieval",
        description="A school of Mahayana Buddhism emphasizing meditation.",
    )
    test_db.add(row)
    await test_db.flush()

    resp = await client.get("/api/v1/traditions/zen")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["slug"] == "zen"
    assert data["name"] == "Zen"
    assert data["description"] == "A school of Mahayana Buddhism emphasizing meditation."


@pytest.mark.asyncio
async def test_get_tradition_returns_404_for_unknown_slug(client):
    resp = await client.get("/api/v1/traditions/does-not-exist")
    assert resp.status_code == 404

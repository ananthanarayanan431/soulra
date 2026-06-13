import pytest
from soulra.models.tradition import Tradition


@pytest.mark.asyncio
async def test_get_tradition_returns_detail_with_description(client, test_db, test_user):
    row = Tradition(
        user_id=test_user.id,
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


@pytest.mark.asyncio
async def test_update_tradition_applies_partial_changes(client, test_db, test_user):
    row = Tradition(user_id=test_user.id, slug="taoism", name="Taoism", origin="China", era="ancient")
    test_db.add(row)
    await test_db.flush()

    resp = await client.put("/api/v1/traditions/taoism", json={"origin": "China · ~600 BCE"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "Taoism"  # unchanged
    assert data["era"] == "ancient"  # unchanged
    assert data["origin"] == "China · ~600 BCE"  # changed


@pytest.mark.asyncio
async def test_update_tradition_returns_404_for_unknown_slug(client):
    resp = await client.put("/api/v1/traditions/does-not-exist", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_tradition_removes_record(client, test_db, test_user):
    row = Tradition(user_id=test_user.id, slug="confucianism", name="Confucianism", origin="China", era="ancient")
    test_db.add(row)
    await test_db.flush()

    resp = await client.delete("/api/v1/traditions/confucianism")
    assert resp.status_code == 204

    resp = await client.get("/api/v1/traditions/confucianism")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_tradition_returns_404_for_unknown_slug(client):
    resp = await client.delete("/api/v1/traditions/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_tradition_same_slug_for_different_users(client, other_client):
    """Two users can each create a tradition with the same slug without conflict."""
    resp1 = await client.post(
        "/api/v1/traditions",
        json={"name": "Stoic", "origin": "Rome", "era": "ancient", "slug": "stoic"},
    )
    assert resp1.status_code == 201

    resp2 = await other_client.post(
        "/api/v1/traditions",
        json={"name": "Stoic", "origin": "Rome", "era": "ancient", "slug": "stoic"},
    )
    assert resp2.status_code == 201


@pytest.mark.asyncio
async def test_list_traditions_only_returns_own_rows(client, other_client, test_db, test_user, other_user):
    test_db.add(Tradition(user_id=test_user.id, slug="stoic", name="Stoic", origin="Rome", era="ancient"))
    test_db.add(Tradition(user_id=other_user.id, slug="zen", name="Zen", origin="Japan", era="medieval"))
    await test_db.flush()

    resp = await client.get("/api/v1/traditions")
    slugs = [t["slug"] for t in resp.json()["data"]["traditions"]]
    assert slugs == ["stoic"]

    resp = await other_client.get("/api/v1/traditions")
    slugs = [t["slug"] for t in resp.json()["data"]["traditions"]]
    assert slugs == ["zen"]

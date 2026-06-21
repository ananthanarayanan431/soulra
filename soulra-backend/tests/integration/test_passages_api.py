import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.documents import Document


@pytest.mark.asyncio
async def test_list_passages_returns_array(client):
    mock_vs = MagicMock()
    mock_vs.asimilarity_search = AsyncMock(return_value=[])
    with patch("soulra.api.v1.passages._get_vs", return_value=mock_vs):
        resp = await client.get("/api/v1/passages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"] == []


@pytest.mark.asyncio
async def test_list_passages_with_tradition_filter(client):
    mock_vs = MagicMock()
    doc = Document(
        page_content="Stoic wisdom.",
        metadata={"id": "p-1", "tradition": "stoic", "author": "Marcus"},
    )
    mock_vs.asimilarity_search = AsyncMock(return_value=[doc])
    with patch("soulra.api.v1.passages._get_vs", return_value=mock_vs):
        resp = await client.get("/api/v1/passages?tradition=stoic")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["tradition"] == "stoic"


@pytest.mark.asyncio
async def test_list_passages_filters_by_current_user(client):
    mock_vs = MagicMock()
    mock_vs.asimilarity_search = AsyncMock(return_value=[])
    with patch("soulra.api.v1.passages._get_vs", return_value=mock_vs):
        resp = await client.get("/api/v1/passages")
    assert resp.status_code == 200
    _, kwargs = mock_vs.asimilarity_search.call_args
    assert kwargs["filter"]["user_id"] == "user_test_primary"


@pytest.mark.asyncio
async def test_delete_passage_returns_204(client):
    mock_vs = MagicMock()
    doc = Document(page_content="x", metadata={"user_id": "user_test_primary"})
    mock_vs.aget_by_ids = AsyncMock(return_value=[doc])
    mock_vs.adelete = AsyncMock(return_value=None)
    with patch("soulra.api.v1.passages._get_vs", return_value=mock_vs):
        resp = await client.delete("/api/v1/passages/passage-abc")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_passage_not_owned_by_user_returns_404(client):
    mock_vs = MagicMock()
    doc = Document(page_content="x", metadata={"user_id": "user_test_other"})
    mock_vs.aget_by_ids = AsyncMock(return_value=[doc])
    mock_vs.adelete = AsyncMock(return_value=None)
    with patch("soulra.api.v1.passages._get_vs", return_value=mock_vs):
        resp = await client.delete("/api/v1/passages/passage-abc")
    assert resp.status_code == 404
    mock_vs.adelete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_passage_missing_returns_404(client):
    mock_vs = MagicMock()
    mock_vs.aget_by_ids = AsyncMock(return_value=[])
    mock_vs.adelete = AsyncMock(return_value=None)
    with patch("soulra.api.v1.passages._get_vs", return_value=mock_vs):
        resp = await client.delete("/api/v1/passages/passage-abc")
    assert resp.status_code == 404
    mock_vs.adelete.assert_not_called()


@pytest.mark.asyncio
async def test_list_collections_returns_collection_name(client):
    mock_vs = MagicMock()
    mock_vs.collection_name = "wisdom_passages"
    with patch("soulra.api.v1.passages._get_vs", return_value=mock_vs):
        resp = await client.get("/api/v1/collections")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"][0]["name"] == "wisdom_passages"


@pytest.mark.asyncio
async def test_list_passages_accepts_offset_param(client):
    """GET /passages must accept offset query param without error."""
    with patch("soulra.api.v1.passages._get_vs") as mock_vs_factory:
        mock_vs = MagicMock()
        mock_vs.asimilarity_search = AsyncMock(return_value=[])
        mock_vs_factory.return_value = mock_vs
        resp = await client.get("/api/v1/passages?offset=10&limit=20")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_passages_rejects_limit_zero(client):
    """limit=0 must be rejected."""
    resp = await client.get("/api/v1/passages?limit=0")
    assert resp.status_code == 422

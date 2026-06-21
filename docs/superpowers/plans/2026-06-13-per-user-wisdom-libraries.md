# Per-User Wisdom Libraries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scope the wisdom corpus (vector store passages + the `traditions` table) per-user, so each user only sees and routes to traditions/passages they personally ingested.

**Architecture:** Add `user_id` to the `traditions` table (composite PK `(user_id, slug)`) and to each embedded chunk's `cmetadata`. Thread `user_id` through the LangGraph `RunnableConfig` (`config["configurable"]["user_id"]`) into `intake` (tradition routing options) and `retrieve` (vector search filter). Scope all `/traditions/*` and `/ingest/*` endpoints to `current_user`.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Alembic, LangGraph, langchain_postgres `PGVector`, pytest + pytest-asyncio.

All commands below assume `cd soulra-backend && source .venv/bin/activate`.

---

### Task 1: Migration — `traditions.user_id` + composite PK + embedding backfill

**Files:**
- Create: `soulra-backend/migrations/versions/0008_traditions_per_user.py`

- [ ] **Step 1: Write the migration**

```python
"""traditions per-user scoping + embedding user_id backfill

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-13

"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

# Sole existing account in the dev DB — owns the existing "mahabharat"
# tradition row and its 1371 embedded chunks. One-time backfill only.
_BACKFILL_USER_ID = "user_3F2yAzuFB9vdrwZIsPNtxMQQmVV"


def upgrade() -> None:
    op.add_column("traditions", sa.Column("user_id", sa.String(length=255), nullable=True))
    op.execute(f"UPDATE traditions SET user_id = '{_BACKFILL_USER_ID}'")
    op.alter_column("traditions", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_traditions_user_id", "traditions", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.drop_constraint("traditions_pkey", "traditions", type_="primary")
    op.create_primary_key("traditions_pkey", "traditions", ["user_id", "slug"])

    op.execute(
        f"""
        UPDATE langchain_pg_embedding
        SET cmetadata = cmetadata || '{{"user_id": "{_BACKFILL_USER_ID}"}}'::jsonb
        WHERE cmetadata->>'tradition' = 'mahabharat'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE langchain_pg_embedding
        SET cmetadata = cmetadata - 'user_id'
        WHERE cmetadata->>'tradition' = 'mahabharat'
        """
    )
    op.drop_constraint("traditions_pkey", "traditions", type_="primary")
    op.create_primary_key("traditions_pkey", "traditions", ["slug"])
    op.drop_constraint("fk_traditions_user_id", "traditions", type_="foreignkey")
    op.drop_column("traditions", "user_id")
```

- [ ] **Step 2: Run the migration**

Run: `alembic upgrade head`
Expected: completes with no errors, `alembic current` now shows `0008 (head)`.

- [ ] **Step 3: Verify the backfill**

Run:
```bash
python3 - <<'EOF'
import asyncio
from sqlalchemy import text
from soulra.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as db:
        r = await db.execute(text("SELECT user_id, slug FROM traditions"))
        print(r.fetchall())
        r = await db.execute(text(
            "SELECT count(*) FROM langchain_pg_embedding WHERE cmetadata->>'user_id' IS NOT NULL"
        ))
        print("embeddings with user_id:", r.scalar())

asyncio.run(main())
EOF
```
Expected: `[('user_3F2yAzuFB9vdrwZIsPNtxMQQmVV', 'mahabharat')]` and `embeddings with user_id: 1371`.

- [ ] **Step 4: Commit**

```bash
git add migrations/versions/0008_traditions_per_user.py
git commit -m "feat: add per-user scoping migration for traditions + embeddings"
```

---

### Task 2: `Tradition` model — composite primary key

**Files:**
- Modify: `soulra-backend/soulra/models/tradition.py`

- [ ] **Step 1: Update the model**

```python
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from soulra.database import Base


class Tradition(Base):
    __tablename__ = "traditions"

    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    slug: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    origin: Mapped[str] = mapped_column(String(120), nullable=False)
    era: Mapped[str] = mapped_column(String(40), nullable=False)
    user_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
```

`user_id` is declared first so `db.get(Tradition, (user_id, slug))` matches primary-key column order.

- [ ] **Step 2: Commit**

```bash
git add soulra/models/tradition.py
git commit -m "feat: add user_id to Tradition model as part of composite PK"
```

(Tests will fail until Task 3 updates `traditions.py` and its tests — that's expected, both land together.)

---

### Task 3: Scope `/traditions/*` endpoints to `current_user`

**Files:**
- Modify: `soulra-backend/soulra/api/v1/traditions.py`
- Test: `soulra-backend/tests/integration/test_traditions_api.py`

- [ ] **Step 1: Update existing tests for per-user `Tradition` rows + auth**

Replace the full contents of `tests/integration/test_traditions_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_traditions_api.py -v`
Expected: FAIL — `TypeError`/`IntegrityError` creating `Tradition` rows without `user_id` is now satisfied by the test rows, but the endpoints in `traditions.py` don't yet filter by `current_user`, so e.g. `test_list_traditions_only_returns_own_rows` fails (`other_client`'s list includes "stoic" too) and `test_create_tradition_same_slug_for_different_users` fails (second create returns 409).

- [ ] **Step 3: Update `traditions.py`**

Replace the full contents of `soulra-backend/soulra/api/v1/traditions.py`:

```python
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from soulra.core.auth import get_current_user
from soulra.database import get_db
from soulra.models.tradition import Tradition
from soulra.models.user import User
from soulra.schemas.responses import SuccessResponse
from soulra.schemas.tradition import (
    CreateTradition,
    PreferencesUpdate,
    TraditionOut,
    TraditionsResponse,
    TraditionUpdate,
)


def _slugify(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")


router = APIRouter(tags=["traditions"])

_COLLECTION = "wisdom_passages"

_COUNTS_SQL = text("""
    SELECT
        cmetadata->>'tradition' AS tradition_slug,
        COUNT(*)::int              AS passages,
        COUNT(DISTINCT cmetadata->>'source')::int AS sources
    FROM langchain_pg_embedding
    WHERE collection_id = (
        SELECT uuid FROM langchain_pg_collection WHERE name = :collection
    )
    AND cmetadata->>'user_id' = :user_id
    GROUP BY cmetadata->>'tradition'
""")


async def _passage_counts(db: AsyncSession, user_id: str) -> dict[str, dict]:
    try:
        rows = (
            await db.execute(_COUNTS_SQL, {"collection": _COLLECTION, "user_id": user_id})
        ).mappings().all()
        return {
            r["tradition_slug"]: {"passages": r["passages"], "sources": r["sources"]}
            for r in rows
            if r["tradition_slug"]
        }
    except Exception:
        return {}


@router.get(
    "/traditions",
    response_model=SuccessResponse[TraditionsResponse],
    summary="List wisdom traditions",
    description="Returns the current user's wisdom traditions with live passage/source counts from the vector store and the current user selection.",
)
async def list_traditions(
    era: str | None = Query(
        default=None, description="Filter by era: ancient, medieval, perennial"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tradition).where(Tradition.user_id == current_user.id).order_by(Tradition.name)
    if era and era != "all":
        stmt = stmt.where(Tradition.era == era)
    rows = (await db.execute(stmt)).scalars().all()
    counts = await _passage_counts(db, current_user.id)

    traditions = []
    for t in rows:
        c = counts.get(t.slug, {"passages": 0, "sources": 0})
        traditions.append(
            TraditionOut(
                slug=t.slug,
                name=t.name,
                origin=t.origin,
                era=t.era,
                sources=c["sources"],
                passages=c["passages"],
                selected=t.user_selected,
                description=t.description,
            )
        )

    return SuccessResponse(
        data=TraditionsResponse(
            traditions=traditions,
            total_sources=sum(t.sources for t in traditions),
            total_passages=sum(t.passages for t in traditions),
        )
    )


@router.get(
    "/eras",
    response_model=SuccessResponse[list[str]],
    summary="List distinct era values",
)
async def list_eras(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tradition.era)
        .where(Tradition.user_id == current_user.id)
        .distinct()
        .order_by(Tradition.era)
    )
    eras = [row[0] for row in result.all()]
    return SuccessResponse(data=eras)


@router.post(
    "/traditions",
    response_model=SuccessResponse[TraditionOut],
    status_code=201,
    summary="Create a new wisdom tradition",
)
async def create_tradition(
    body: CreateTradition,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    slug = body.slug or _slugify(body.name)
    if await db.get(Tradition, (current_user.id, slug)):
        raise HTTPException(status_code=409, detail=f"Tradition '{slug}' already exists")
    tradition = Tradition(
        user_id=current_user.id,
        slug=slug,
        name=body.name,
        origin=body.origin,
        era=body.era,
        user_selected=False,
        description=body.description,
    )
    db.add(tradition)
    await db.commit()
    await db.refresh(tradition)
    return SuccessResponse(
        data=TraditionOut(
            slug=tradition.slug,
            name=tradition.name,
            origin=tradition.origin,
            era=tradition.era,
            sources=0,
            passages=0,
            selected=False,
            description=tradition.description,
        )
    )


@router.put(
    "/traditions/preferences",
    status_code=204,
    summary="Update tradition selection",
    description="Replaces the current tradition selection. Pass the complete list of selected slugs.",
)
async def update_preferences(
    body: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    selected_set = set(body.selected)
    rows = (
        await db.execute(select(Tradition).where(Tradition.user_id == current_user.id))
    ).scalars().all()
    for t in rows:
        t.user_selected = t.slug in selected_set
    await db.commit()


@router.get(
    "/traditions/{slug}",
    response_model=SuccessResponse[TraditionOut],
    summary="Get a wisdom tradition",
    description="Fetches a single tradition owned by the current user, including live passage/source counts. Returns 404 if the slug doesn't exist for this user.",
)
async def get_tradition(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Tradition, (current_user.id, slug))
    if row is None:
        raise HTTPException(status_code=404, detail="Tradition not found")
    counts = await _passage_counts(db, current_user.id)
    c = counts.get(row.slug, {"passages": 0, "sources": 0})
    return SuccessResponse(
        data=TraditionOut(
            slug=row.slug,
            name=row.name,
            origin=row.origin,
            era=row.era,
            sources=c["sources"],
            passages=c["passages"],
            selected=row.user_selected,
            description=row.description,
        )
    )


@router.put(
    "/traditions/{slug}",
    response_model=SuccessResponse[TraditionOut],
    summary="Update a wisdom tradition",
    description="Partially updates a tradition owned by the current user — only the provided fields change. The slug is immutable. Returns 404 if the slug doesn't exist for this user.",
)
async def update_tradition(
    slug: str,
    body: TraditionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Tradition, (current_user.id, slug))
    if row is None:
        raise HTTPException(status_code=404, detail="Tradition not found")

    if body.name is not None:
        row.name = body.name
    if body.origin is not None:
        row.origin = body.origin
    if body.era is not None:
        row.era = body.era
    if body.description is not None:
        row.description = body.description
    await db.commit()
    await db.refresh(row)

    counts = await _passage_counts(db, current_user.id)
    c = counts.get(row.slug, {"passages": 0, "sources": 0})
    return SuccessResponse(
        data=TraditionOut(
            slug=row.slug,
            name=row.name,
            origin=row.origin,
            era=row.era,
            sources=c["sources"],
            passages=c["passages"],
            selected=row.user_selected,
            description=row.description,
        )
    )


@router.delete(
    "/traditions/{slug}",
    status_code=204,
    summary="Delete a wisdom tradition",
    description="Permanently removes a tradition owned by the current user. Returns 404 if the slug doesn't exist for this user, otherwise 204 No Content.",
)
async def delete_tradition(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(Tradition, (current_user.id, slug))
    if row is None:
        raise HTTPException(status_code=404, detail="Tradition not found")
    await db.delete(row)
    await db.commit()
    return Response(status_code=204)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/integration/test_traditions_api.py -v`
Expected: all PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add soulra/api/v1/traditions.py tests/integration/test_traditions_api.py
git commit -m "feat: scope traditions API endpoints to current_user"
```

---

### Task 4: `WisdomRetriever.search()` — accept `user_id` filter

**Files:**
- Modify: `soulra-backend/soulra/services/retrieval/retriever.py`
- Test: `soulra-backend/tests/unit/test_retriever.py`

- [ ] **Step 1: Check for an existing retriever test file**

Run: `ls tests/unit/test_retriever.py 2>/dev/null || echo "none"`

If "none", create `tests/unit/test_retriever.py` with the content below. If it exists, add the test function to it.

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.documents import Document


@pytest.mark.asyncio
async def test_search_filters_by_user_id_and_tradition():
    from soulra.services.retrieval.retriever import WisdomRetriever

    vs = MagicMock()
    vs.asimilarity_search = AsyncMock(return_value=[Document(page_content="x", metadata={})])
    retriever = WisdomRetriever(vs)

    await retriever.search("query", tradition_filter="stoic", user_id="user_123", k=10)

    vs.asimilarity_search.assert_awaited_once_with(
        "query", k=10, filter={"tradition": "stoic", "user_id": "user_123"}
    )


@pytest.mark.asyncio
async def test_search_filters_by_user_id_only_when_no_tradition():
    from soulra.services.retrieval.retriever import WisdomRetriever

    vs = MagicMock()
    vs.asimilarity_search = AsyncMock(return_value=[])
    retriever = WisdomRetriever(vs)

    await retriever.search("query", tradition_filter=None, user_id="user_123", k=5)

    vs.asimilarity_search.assert_awaited_once_with(
        "query", k=5, filter={"user_id": "user_123"}
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_retriever.py -v`
Expected: FAIL — `TypeError: search() got an unexpected keyword argument 'user_id'`.

- [ ] **Step 3: Update `retriever.py`**

```python
import hashlib

from langchain_core.documents import Document
from langchain_postgres import PGVector
from soulra.core.exceptions import RetrievalError
from soulra.core.logging import logger


class WisdomRetriever:
    def __init__(self, vectorstore: PGVector):
        self.vectorstore = vectorstore

    async def search(
        self,
        query: str,
        tradition_filter: str | None = None,
        user_id: str | None = None,
        k: int = 5,
    ) -> list[Document]:
        try:
            kwargs: dict = {"k": k}
            filter_dict: dict = {}
            if tradition_filter:
                filter_dict["tradition"] = tradition_filter
            if user_id:
                filter_dict["user_id"] = user_id
            if filter_dict:
                kwargs["filter"] = filter_dict
            return await self.vectorstore.asimilarity_search(query, **kwargs)
        except Exception as e:
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:12]
            logger.error("retrieval_failed", query_hash=query_hash, error=str(e))
            raise RetrievalError(f"Vector search failed: {e}") from e
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_retriever.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full retrieve/grade test file to check for regressions**

Run: `pytest tests/unit/test_node_retrieve_grade.py -v`
Expected: all PASS (existing `retrieve` tests don't pass `user_id`, which defaults to `None` and is omitted from the filter — no behavior change for them).

- [ ] **Step 6: Commit**

```bash
git add soulra/services/retrieval/retriever.py tests/unit/test_retriever.py
git commit -m "feat: filter vector search by user_id in WisdomRetriever"
```

---

### Task 5: `retrieve` node — read `user_id` from config

**Files:**
- Modify: `soulra-backend/soulra/graph/nodes/retrieve.py`
- Test: `soulra-backend/tests/unit/test_node_retrieve_grade.py`

- [ ] **Step 1: Add a failing test**

Add this test to `tests/unit/test_node_retrieve_grade.py` (near the other `retrieve` tests):

```python
@pytest.mark.asyncio
async def test_retrieve_node_passes_user_id_from_config(mock_vectorstore):
    from soulra.graph.nodes.retrieve import create_retrieve_node
    from soulra.services.retrieval.retriever import WisdomRetriever

    retriever = WisdomRetriever(mock_vectorstore)
    retrieve = create_retrieve_node(retriever)

    config = {"configurable": {"user_id": "user_123"}}
    await retrieve(_make_state(), config)

    for call in mock_vectorstore.asimilarity_search.call_args_list:
        assert call.kwargs["filter"]["user_id"] == "user_123"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_node_retrieve_grade.py::test_retrieve_node_passes_user_id_from_config -v`
Expected: FAIL — `TypeError: retrieve() missing 1 required positional argument: 'config'`.

- [ ] **Step 3: Update `retrieve.py`**

```python
# app/graph/nodes/retrieve.py
import asyncio
from typing import cast

from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from soulra.graph.state import SoulraState
from soulra.services.retrieval.retriever import WisdomRetriever


def create_retrieve_node(retriever: WisdomRetriever, output_key: str = "retrieved_docs"):
    async def retrieve(state: SoulraState, config: RunnableConfig) -> dict:
        query = state["query"]
        hints = cast("list[str | None]", state["tradition_hints"] or [None])
        user_id = config.get("configurable", {}).get("user_id")

        results = await asyncio.gather(
            *[
                retriever.search(query, tradition_filter=hint, user_id=user_id, k=10)
                for hint in hints
            ]
        )

        all_docs: list[Document] = []
        seen_contents: set[str] = set()
        for docs in results:
            for doc in docs:
                if doc.page_content not in seen_contents:
                    all_docs.append(doc)
                    seen_contents.add(doc.page_content)

        return {output_key: all_docs}

    return retrieve
```

- [ ] **Step 4: Update existing `retrieve` test calls to pass `config`**

In `tests/unit/test_node_retrieve_grade.py`, every `await retrieve(...)` and `await retrieve_refined(...)` call needs a second `{}` argument (empty config — `user_id` will be `None`, omitted from the filter). Update these calls:

- `test_retrieve_node_calls_retriever_for_each_hint`: `await retrieve(_make_state())` → `await retrieve(_make_state(), {})`
- `test_retrieve_node_deduplicates_documents`: `await retrieve(_make_state())` → `await retrieve(_make_state(), {})`
- `test_retrieve_refined_writes_to_refined_docs_key`: `await retrieve_refined(_make_state())` → `await retrieve_refined(_make_state(), {})`
- `test_retrieve_node_searches_traditions_concurrently`: `await retrieve(state)` → `await retrieve(state, {})`
- `test_retrieve_node_requests_k10_per_tradition`: `await retrieve(_make_state())` → `await retrieve(_make_state(), {})`

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_node_retrieve_grade.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add soulra/graph/nodes/retrieve.py tests/unit/test_node_retrieve_grade.py
git commit -m "feat: thread user_id from config into retrieve node"
```

---

### Task 6: `intake` node — scope `get_tradition_options` by `user_id`

**Files:**
- Modify: `soulra-backend/soulra/graph/nodes/intake.py`
- Test: `soulra-backend/tests/unit/test_node_intake.py`

- [ ] **Step 1: Add a failing test**

Add this test to `tests/unit/test_node_intake.py`:

```python
@pytest.mark.asyncio
async def test_get_tradition_options_filters_by_user_id():
    from soulra.graph.nodes.intake import get_tradition_options

    class FakeResult:
        def all(self):
            return [("mahabharat",)]

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def execute(self, stmt):
            self.captured_stmt = stmt
            return FakeResult()

    fake_session = FakeSession()

    with patch(
        "soulra.graph.nodes.intake.AsyncSessionLocal",
        return_value=fake_session,
    ):
        options = await get_tradition_options("user_123")

    assert options == ["mahabharat"]
    # The compiled query must reference user_id (i.e. it's filtered, not a bare select-all)
    compiled = str(fake_session.captured_stmt)
    assert "user_id" in compiled
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_node_intake.py::test_get_tradition_options_filters_by_user_id -v`
Expected: FAIL — `TypeError: get_tradition_options() takes 0 positional arguments but 1 was given`.

- [ ] **Step 3: Update `intake.py`**

```python
# app/graph/nodes/intake.py
from typing import cast

from pydantic import BaseModel
from sqlalchemy import select
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from soulra.database import AsyncSessionLocal
from soulra.graph.state import SoulraState
from soulra.models.tradition import Tradition

DEFAULT_TRADITION_OPTIONS = [
    "stoic",
    "vedanta",
    "buddhist",
    "sufi",
    "taoist",
    "jewish",
    "christian_mystic",
    "zen",
]


async def get_tradition_options(user_id: str | None) -> list[str]:
    """Tradition slugs the intake LLM can route to for this user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Tradition.slug).where(Tradition.user_id == user_id)
        )
        slugs = [row[0] for row in result.all()]
    return slugs or DEFAULT_TRADITION_OPTIONS


INTAKE_PROMPT = """You are helping route a user's situation to the right wisdom traditions.
Given this situation: {situation}

Extract:
1. tradition_hints: list of 2-3 most relevant traditions from {options}
2. query: a clear, concise search query (max 15 words) capturing the core problem

Respond with a JSON object with keys "tradition_hints" and "query"."""

MAX_TRADITION_HINTS = 5
MAX_HINT_LENGTH = 50


class IntakeOutput(BaseModel):
    tradition_hints: list[str]
    query: str


def _sanitize_hints(hints: list) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for h in hints:
        if not isinstance(h, str):
            continue
        h = h.strip()[:MAX_HINT_LENGTH]
        if not h or h in seen:
            continue
        seen.add(h)
        result.append(h)
        if len(result) >= MAX_TRADITION_HINTS:
            break
    return result


def create_intake_node(llm: ChatOpenAI):
    structured_llm = llm.with_structured_output(IntakeOutput)

    async def intake(state: SoulraState, config: RunnableConfig) -> dict:
        user_id = config.get("configurable", {}).get("user_id")
        options = await get_tradition_options(user_id)
        prompt = INTAKE_PROMPT.format(
            situation=state["situation"],
            options=options,
        )
        result = cast(IntakeOutput, await structured_llm.ainvoke(prompt, config=config))
        return {
            "tradition_hints": _sanitize_hints(result.tradition_hints),
            "query": result.query,
            "rewrite_count": 0,
        }

    return intake
```

- [ ] **Step 4: Update the two existing intake tests' patched return signature**

The two existing tests (`test_intake_extracts_tradition_hints`, `test_intake_initialises_rewrite_count`) already patch `get_tradition_options` with `AsyncMock(return_value=[...])` and call `intake(_make_empty_state(), {})`. Since `get_tradition_options` is now patched wholesale (not the real function), it accepts any argument — no change needed to these two tests.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_node_intake.py -v`
Expected: all PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add soulra/graph/nodes/intake.py tests/unit/test_node_intake.py
git commit -m "feat: scope intake tradition options by user_id"
```

---

### Task 7: Thread `user_id` into the graph config from the websocket handler

**Files:**
- Modify: `soulra-backend/soulra/api/websocket.py`

- [ ] **Step 1: Update the config dict**

In `soulra/api/websocket.py`, find:

```python
            config = {"configurable": {"thread_id": thread_id}, "callbacks": [usage_cb]}
```

Replace with:

```python
            config = {
                "configurable": {"thread_id": thread_id, "user_id": current_user.id},
                "callbacks": [usage_cb],
            }
```

- [ ] **Step 2: Run the websocket test suite**

Run: `pytest tests/ -k websocket -v`
Expected: all PASS (no behavioral change to existing assertions — this only adds a key to `config["configurable"]`).

- [ ] **Step 3: Commit**

```bash
git add soulra/api/websocket.py
git commit -m "feat: pass user_id into graph config for retrieval/intake scoping"
```

---

### Task 8: Tag ingested chunks with `user_id`

**Files:**
- Modify: `soulra-backend/soulra/api/v1/ingest.py`
- Test: `soulra-backend/tests/integration/test_ingest_api.py`

- [ ] **Step 1: Inspect existing ingest tests for the metadata assertion pattern**

Run: `grep -n "metadata\|run_ingest.delay\|_dispatch" tests/integration/test_ingest_api.py`

(These tests mock `run_ingest.delay` — note from the conversation history that 3 of them already fail for unrelated reasons (`test_ingest_pdf_returns_job_id`, `test_ingest_text_returns_job_id`, `test_ingest_url_returns_job_id`). Don't try to fix those pre-existing failures; just confirm this task doesn't make them worse and doesn't change their failure mode.)

- [ ] **Step 2: Add `user_id` to each endpoint's metadata dict**

In `soulra/api/v1/ingest.py`, update the `metadata` dict construction in all four endpoints:

`ingest_pdf` — change:
```python
    metadata = {"tradition": tradition, "author": author, "source": source, "era": era}
```
to:
```python
    metadata = {
        "tradition": tradition,
        "author": author,
        "source": source,
        "era": era,
        "user_id": current_user.id,
    }
```

Apply the same change to `ingest_text`, `ingest_url`, and `ingest_youtube` (each has an identical `metadata = {...}` line).

- [ ] **Step 3: Run the ingest test suite**

Run: `pytest tests/integration/test_ingest_api.py -v`
Expected: same 3 pre-existing failures as before this task (unchanged failure messages — confirm with `git stash` / `git stash pop` comparison if unsure), all other tests PASS.

- [ ] **Step 4: Commit**

```bash
git add soulra/api/v1/ingest.py
git commit -m "feat: tag ingested chunks with user_id for per-user retrieval"
```

---

### Task 9: Full suite + lint/typecheck

- [ ] **Step 1: Run the full backend test suite**

Run: `pytest -q`
Expected: same 4 pre-existing failures as the project baseline (`test_ingest_pdf_returns_job_id`, `test_ingest_text_returns_job_id`, `test_ingest_url_returns_job_id`, `test_clerk_and_token_limit_defaults`), all others PASS — net new tests from this plan all green.

- [ ] **Step 2: Run ruff and mypy**

Run: `ruff check soulra/ tests/ && mypy soulra/`
Expected: ruff "All checks passed!"; mypy shows only the pre-existing `celery_app.py` import-untyped error.

- [ ] **Step 3: Manual verification (requires running stack)**

With the backend + frontend running and a real chat conversation:
- `grade_skipped_empty_reranked_docs` should stop appearing for situations where the intake LLM routes to `"mahabharat"` (your account now owns those embeddings).
- `/api/v1/traditions` should return only your "mahabharat" tradition.
- `token_usage_log` should gain rows after the conversation completes (already fixed in a prior change, verify it still works).

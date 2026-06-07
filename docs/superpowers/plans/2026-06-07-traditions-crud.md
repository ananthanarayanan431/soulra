# User-Managed Wisdom Traditions (CRUD) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users create, edit, and delete their own wisdom traditions from the `/traditions` page (replacing the fixed 9-tradition seed list), with a popover that surfaces each tradition's `description`, and era filter chips computed dynamically from the live data.

**Architecture:** Extend the existing `soulra/api/v1/traditions.py` router with `GET/PUT/DELETE /traditions/{slug}` (the `POST /traditions` create endpoint and `_slugify` helper already exist), thread the `description` field through `TraditionOut`, strip the seed data from migration `0002`, and rewrite `TraditionsClient.tsx` to hold traditions as local state so create/edit/delete update the UI without a page reload.

**Tech Stack:** FastAPI + SQLAlchemy async ORM + Pydantic (backend), Next.js client component + Tailwind (frontend), pytest-asyncio + httpx `AsyncClient` (tests).

---

## Important context for the engineer

- The codebase **already has** `POST /traditions` (`create_tradition`), a `_slugify` helper, `CreateTradition` schema, and a `GET /eras` endpoint in `soulra/api/v1/traditions.py` — these were added in an earlier commit. **Do not recreate them.** This plan only adds what's missing: `GET/PUT/DELETE /traditions/{slug}`, the `description` field on responses, the `TraditionUpdate` schema, and the frontend pieces.
- Route registration order matters: `PUT /traditions/preferences` (a literal path) is already registered before where you'll add `PUT /traditions/{slug}` (a parameterized path). Keep the new `{slug}` routes appended **after** `update_preferences` in the file so Starlette matches the literal path first.
- The backend dev server runs with `--reload` on port 8000 and the frontend on port 3000 — both already running. Code changes apply automatically; you don't need to restart them.
- Run backend commands from `/Volumes/External/soulra/soulra-backend` using `.venv/bin/pytest` / `.venv/bin/python` (matches the project `Makefile`).
- `SuccessResponse[T]` wraps all success payloads as `{"success": true, "data": ...}`; `HTTPException(status_code=...)` produces `{"detail": "..."}` on errors — the frontend reads `json.detail`.

---

## Task 1: Add `description` to `TraditionOut` + `GET /traditions/{slug}`

**Files:**
- Modify: `soulra-backend/soulra/schemas/tradition.py`
- Modify: `soulra-backend/soulra/api/v1/traditions.py`
- Modify: `soulra-backend/tests/conftest.py`
- Test: `soulra-backend/tests/integration/test_traditions_api.py` (new file)

- [ ] **Step 1: Register the `Tradition` model with the test database**

The `traditions` table currently isn't created in the in-memory test DB because `Tradition` is never imported in `conftest.py` (SQLAlchemy only registers tables for models it has seen). Add the import alongside the existing ones:

In `soulra-backend/tests/conftest.py`, change:
```python
from soulra.models.conversation import Conversation, ActionStep  # noqa: F401
from soulra.models.ingest_job import IngestJob  # noqa: F401
```
to:
```python
from soulra.models.conversation import Conversation, ActionStep  # noqa: F401
from soulra.models.ingest_job import IngestJob  # noqa: F401
from soulra.models.tradition import Tradition  # noqa: F401
```

- [ ] **Step 2: Write the failing tests for `GET /traditions/{slug}`**

Create `soulra-backend/tests/integration/test_traditions_api.py`:
```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Volumes/External/soulra/soulra-backend && .venv/bin/pytest tests/integration/test_traditions_api.py -v`
Expected: both tests FAIL — `test_get_tradition_returns_detail_with_description` with a `KeyError: 'description'` (field missing from the response) and/or a 404 from the route not existing; `test_get_tradition_returns_404_for_unknown_slug` may pass by accident (FastAPI 404s unmatched routes too) — that's fine, it'll be exercising the real route once Step 5 lands.

- [ ] **Step 4: Add `description` to `TraditionOut`**

In `soulra-backend/soulra/schemas/tradition.py`, change:
```python
class TraditionOut(BaseModel):
    slug: str
    name: str
    origin: str
    era: str
    sources: int
    passages: int
    selected: bool

    model_config = {"from_attributes": True}
```
to:
```python
class TraditionOut(BaseModel):
    slug: str
    name: str
    origin: str
    era: str
    sources: int
    passages: int
    selected: bool
    description: str | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Add `GET /traditions/{slug}` and thread `description` through existing responses**

In `soulra-backend/soulra/api/v1/traditions.py`:

1. In `list_traditions`, add `description=t.description,` to the `TraditionOut(...)` construction (after `selected=t.user_selected,`).
2. In `create_tradition`, add `description=tradition.description,` to the `TraditionOut(...)` construction (after `selected=False,`).
3. Append this new endpoint immediately after `update_preferences` (the last function in the file):

```python
@router.get(
    "/traditions/{slug}",
    response_model=SuccessResponse[TraditionOut],
    summary="Get a wisdom tradition",
    description="Fetches a single tradition by slug, including live passage/source counts. Returns 404 if the slug doesn't exist.",
)
async def get_tradition(slug: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(Tradition, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Tradition not found")
    counts = await _passage_counts(db)
    c = counts.get(row.slug, {"passages": 0, "sources": 0})
    return SuccessResponse(data=TraditionOut(
        slug=row.slug,
        name=row.name,
        origin=row.origin,
        era=row.era,
        sources=c["sources"],
        passages=c["passages"],
        selected=row.user_selected,
        description=row.description,
    ))
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Volumes/External/soulra/soulra-backend && .venv/bin/pytest tests/integration/test_traditions_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
cd /Volumes/External/soulra
git add soulra-backend/soulra/schemas/tradition.py soulra-backend/soulra/api/v1/traditions.py soulra-backend/tests/conftest.py soulra-backend/tests/integration/test_traditions_api.py
git commit -m "feat: add GET /traditions/{slug} and surface description field"
```

---

## Task 2: Add `PUT /traditions/{slug}` (update)

**Files:**
- Modify: `soulra-backend/soulra/schemas/tradition.py`
- Modify: `soulra-backend/soulra/api/v1/traditions.py`
- Test: `soulra-backend/tests/integration/test_traditions_api.py`

- [ ] **Step 1: Write the failing tests**

Append to `soulra-backend/tests/integration/test_traditions_api.py`:
```python
@pytest.mark.asyncio
async def test_update_tradition_applies_partial_changes(client, test_db):
    row = Tradition(slug="taoism", name="Taoism", origin="China", era="ancient")
    test_db.add(row)
    await test_db.flush()

    resp = await client.put("/api/v1/traditions/taoism", json={"origin": "China · ~600 BCE"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "Taoism"            # unchanged
    assert data["era"] == "ancient"             # unchanged
    assert data["origin"] == "China · ~600 BCE"  # changed


@pytest.mark.asyncio
async def test_update_tradition_returns_404_for_unknown_slug(client):
    resp = await client.put("/api/v1/traditions/does-not-exist", json={"name": "X"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Volumes/External/soulra/soulra-backend && .venv/bin/pytest tests/integration/test_traditions_api.py -v`
Expected: the two new tests FAIL with 404/405 (route doesn't exist yet)

- [ ] **Step 3: Add the `TraditionUpdate` schema**

In `soulra-backend/soulra/schemas/tradition.py`, add after `CreateTradition`:
```python
class TraditionUpdate(BaseModel):
    name: str | None = None
    origin: str | None = None
    era: str | None = None
    description: str | None = None
```

- [ ] **Step 4: Implement `PUT /traditions/{slug}`**

In `soulra-backend/soulra/api/v1/traditions.py`:

1. Add `TraditionUpdate` to the schema import line:
```python
from soulra.schemas.tradition import CreateTradition, PreferencesUpdate, TraditionOut, TraditionsResponse, TraditionUpdate
```
2. Append after `get_tradition`:
```python
@router.put(
    "/traditions/{slug}",
    response_model=SuccessResponse[TraditionOut],
    summary="Update a wisdom tradition",
    description="Partially updates a tradition's name, origin, era, or description — only the provided fields change. The slug is immutable. Returns 404 if the slug doesn't exist.",
)
async def update_tradition(slug: str, body: TraditionUpdate, db: AsyncSession = Depends(get_db)):
    row = await db.get(Tradition, slug)
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

    counts = await _passage_counts(db)
    c = counts.get(row.slug, {"passages": 0, "sources": 0})
    return SuccessResponse(data=TraditionOut(
        slug=row.slug,
        name=row.name,
        origin=row.origin,
        era=row.era,
        sources=c["sources"],
        passages=c["passages"],
        selected=row.user_selected,
        description=row.description,
    ))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Volumes/External/soulra/soulra-backend && .venv/bin/pytest tests/integration/test_traditions_api.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
cd /Volumes/External/soulra
git add soulra-backend/soulra/schemas/tradition.py soulra-backend/soulra/api/v1/traditions.py soulra-backend/tests/integration/test_traditions_api.py
git commit -m "feat: add PUT /traditions/{slug} for partial updates"
```

---

## Task 3: Add `DELETE /traditions/{slug}`

**Files:**
- Modify: `soulra-backend/soulra/api/v1/traditions.py`
- Test: `soulra-backend/tests/integration/test_traditions_api.py`

- [ ] **Step 1: Write the failing tests**

Append to `soulra-backend/tests/integration/test_traditions_api.py`:
```python
@pytest.mark.asyncio
async def test_delete_tradition_removes_record(client, test_db):
    row = Tradition(slug="sufism", name="Sufism", origin="Persia · ~900 CE", era="medieval")
    test_db.add(row)
    await test_db.flush()

    resp = await client.delete("/api/v1/traditions/sufism")
    assert resp.status_code == 204

    follow_up = await client.get("/api/v1/traditions/sufism")
    assert follow_up.status_code == 404


@pytest.mark.asyncio
async def test_delete_tradition_returns_404_for_unknown_slug(client):
    resp = await client.delete("/api/v1/traditions/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_recreate_tradition_after_delete(client):
    body = {"name": "Sufism", "origin": "Persia · ~900 CE", "era": "medieval", "slug": "sufism"}
    first = await client.post("/api/v1/traditions", json=body)
    assert first.status_code == 201

    deleted = await client.delete("/api/v1/traditions/sufism")
    assert deleted.status_code == 204

    second = await client.post("/api/v1/traditions", json=body)
    assert second.status_code == 201
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Volumes/External/soulra/soulra-backend && .venv/bin/pytest tests/integration/test_traditions_api.py -v`
Expected: the three new tests FAIL (DELETE route doesn't exist → 405/404)

- [ ] **Step 3: Implement `DELETE /traditions/{slug}`**

Append to `soulra-backend/soulra/api/v1/traditions.py`, after `update_tradition`:
```python
@router.delete(
    "/traditions/{slug}",
    status_code=204,
    summary="Delete a wisdom tradition",
    description="Removes a tradition from the catalog by slug. Does not cascade — passages already ingested under that slug remain in the vector store untouched. Returns 404 if the slug doesn't exist.",
)
async def delete_tradition(slug: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(Tradition, slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Tradition not found")
    await db.delete(row)
    await db.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Volumes/External/soulra/soulra-backend && .venv/bin/pytest tests/integration/test_traditions_api.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
cd /Volumes/External/soulra
git add soulra-backend/soulra/api/v1/traditions.py soulra-backend/tests/integration/test_traditions_api.py
git commit -m "feat: add DELETE /traditions/{slug}"
```

---

## Task 4: Remove seed data from migration & blank-slate the dev DB

**Files:**
- Modify: `soulra-backend/migrations/versions/0002_traditions.py`

- [ ] **Step 1: Strip the seed rows from the migration**

Replace the entire contents of `soulra-backend/migrations/versions/0002_traditions.py` with:
```python
"""traditions

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-07

"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "traditions",
        sa.Column("slug",          sa.String(80),  primary_key=True),
        sa.Column("name",          sa.String(120), nullable=False),
        sa.Column("origin",        sa.String(120), nullable=False),
        sa.Column("era",           sa.String(40),  nullable=False),
        sa.Column("user_selected", sa.Boolean(),   nullable=False, server_default=sa.false()),
        sa.Column("description",   sa.Text(),      nullable=True),
        sa.PrimaryKeyConstraint("slug"),
    )


def downgrade() -> None:
    op.drop_table("traditions")
```

This makes fresh installs start with an empty `traditions` table — `GET /traditions` returns `{traditions: [], total_sources: 0, total_passages: 0}` until the user creates their own.

- [ ] **Step 2: Clear the 9 seeded rows from the existing local dev database**

The migration change only affects *future* installs — the user's current dev database already has the 9 seeded rows from when `0002` first ran. Running `alembic downgrade`/`upgrade` would cascade through migrations `0003` and `0004` and risk destroying unrelated dev data, so instead run a one-off script using the app's existing async session machinery:

Run: 
```bash
cd /Volumes/External/soulra/soulra-backend && .venv/bin/python -c "
import asyncio
from sqlalchemy import delete
from soulra.database import AsyncSessionLocal
from soulra.models.tradition import Tradition

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(delete(Tradition))
        await session.commit()
        print(f'Deleted {result.rowcount} tradition rows')

asyncio.run(main())
"
```
Expected output: `Deleted 9 tradition rows`

- [ ] **Step 3: Verify the dev DB is now empty**

Run: `curl -s http://localhost:8000/api/v1/traditions | python3 -m json.tool`
Expected: `"traditions": []`, `"total_sources": 0`, `"total_passages": 0`

- [ ] **Step 4: Commit**

```bash
cd /Volumes/External/soulra
git add soulra-backend/migrations/versions/0002_traditions.py
git commit -m "feat: ship traditions table empty — users build their own list"
```

(The DB-clearing script in Step 2 is a one-time operational action, not a code change — nothing from it gets committed.)

---

## Task 5: Add `updateTradition`/`deleteTradition`/`TraditionInput` to the frontend API client

**Files:**
- Modify: `lib/api.ts`

- [ ] **Step 1: Add `description` to the `Tradition` interface**

In `lib/api.ts`, change:
```typescript
export interface Tradition {
  slug: string;
  name: string;
  origin: string;
  era: string;
  sources: number;
  passages: number;
  selected: boolean;
}
```
to:
```typescript
export interface Tradition {
  slug: string;
  name: string;
  origin: string;
  era: string;
  sources: number;
  passages: number;
  selected: boolean;
  description?: string;
}
```

- [ ] **Step 2: Introduce `TraditionInput` and refactor `createTradition` to use it**

Replace the existing `createTradition` function:
```typescript
export async function createTradition(body: {
  name: string;
  origin: string;
  era: string;
  slug?: string;
  description?: string;
}): Promise<Tradition> {
  const res = await fetch(`${BASE}/api/v1/traditions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json?.detail ?? `HTTP ${res.status}`);
  }
  const json = await res.json();
  return json.data as Tradition;
}
```
with:
```typescript
export interface TraditionInput {
  name: string;
  origin: string;
  era: string;
  slug?: string;
  description?: string;
}

export async function createTradition(body: TraditionInput): Promise<Tradition> {
  const res = await fetch(`${BASE}/api/v1/traditions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json?.detail ?? `HTTP ${res.status}`);
  }
  const json = await res.json();
  return json.data as Tradition;
}

export async function updateTradition(slug: string, body: Partial<TraditionInput>): Promise<Tradition> {
  const res = await fetch(`${BASE}/api/v1/traditions/${encodeURIComponent(slug)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json?.detail ?? `HTTP ${res.status}`);
  }
  const json = await res.json();
  return json.data as Tradition;
}

export async function deleteTradition(slug: string): Promise<void> {
  const res = await fetch(`${BASE}/api/v1/traditions/${encodeURIComponent(slug)}`, { method: "DELETE" });
  if (!res.ok) {
    const json = await res.json().catch(() => ({}));
    throw new Error(json?.detail ?? `HTTP ${res.status}`);
  }
}
```

- [ ] **Step 3: Verify the frontend still compiles**

Run: `cd /Volumes/External/soulra && npx tsc --noEmit`
Expected: no new type errors related to `lib/api.ts`

- [ ] **Step 4: Commit**

```bash
cd /Volumes/External/soulra
git add lib/api.ts
git commit -m "feat: add updateTradition/deleteTradition client functions"
```

---

## Task 6: Rewrite `TraditionsClient.tsx` — local state, dynamic eras, create/edit/delete/info

**Files:**
- Modify: `components/screens/TraditionsClient.tsx`

This is the big UI task: traditions become local state (so mutations update the screen instantly), the hardcoded `ERAS` constant is replaced with eras derived from the live data, and each card gains hover-revealed edit/delete actions plus an info-icon popover. Because these pieces share state (`closeOverlays`, `selectedSlugs`, etc.), it's safer to replace the whole file at once than to layer in partial edits.

- [ ] **Step 1: Replace the full file content**

Replace the entire contents of `components/screens/TraditionsClient.tsx` with:

```tsx
"use client";
import { useState, useTransition, type FormEvent, type ReactNode } from "react";
import { Sidebar } from "@/components/layout";
import { Chip } from "@/components/ui";
import type { Tradition, TraditionInput, TraditionsData } from "@/lib/api";
import {
  updateTraditionPreferences,
  createTradition,
  updateTradition,
  deleteTradition,
} from "@/lib/api";

const EMPTY_FORM = { name: "", origin: "", era: "", description: "" };

function slugify(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, "")
    .replace(/[\s_]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="font-mono text-[9px] text-muted uppercase tracking-widest block mb-1">{label}</label>
      {children}
    </div>
  );
}

export function TraditionsClient({ initialData }: { initialData: TraditionsData }) {
  const [traditions, setTraditions] = useState<Tradition[]>(initialData.traditions);
  const [selectedEra, setSelectedEra] = useState<string>("all");
  const [selectedSlugs, setSelectedSlugs] = useState<Set<string>>(
    () => new Set(initialData.traditions.filter(t => t.selected).map(t => t.slug))
  );
  const [, startTransition] = useTransition();

  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState(EMPTY_FORM);
  const [createBusy, setCreateBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [editBusy, setEditBusy] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [confirmingSlug, setConfirmingSlug] = useState<string | null>(null);
  const [infoSlug, setInfoSlug] = useState<string | null>(null);

  const eras = ["all", ...Array.from(new Set(traditions.map(t => t.era))).sort()];
  const visible = selectedEra === "all" ? traditions : traditions.filter(t => t.era === selectedEra);
  const selectedTraditions = traditions.filter(t => selectedSlugs.has(t.slug));
  const totalSources = traditions.reduce((sum, t) => sum + t.sources, 0);
  const totalPassages = traditions.reduce((sum, t) => sum + t.passages, 0);

  function closeOverlays() {
    setShowCreate(false);
    setEditingSlug(null);
    setConfirmingSlug(null);
    setInfoSlug(null);
  }

  function toggleTradition(slug: string) {
    const next = new Set(selectedSlugs);
    next.has(slug) ? next.delete(slug) : next.add(slug);
    const slugs = Array.from(next);
    setSelectedSlugs(next);
    startTransition(() => { updateTraditionPreferences(slugs); });
  }

  function toggleCreateForm() {
    if (showCreate) {
      setShowCreate(false);
      return;
    }
    closeOverlays();
    setCreateForm(EMPTY_FORM);
    setCreateError(null);
    setShowCreate(true);
  }

  async function handleCreateSubmit(e: FormEvent) {
    e.preventDefault();
    const name = createForm.name.trim();
    const origin = createForm.origin.trim();
    const era = createForm.era.trim();
    if (!name || !origin || !era) return;

    setCreateBusy(true);
    setCreateError(null);
    try {
      const input: TraditionInput = { name, origin, era };
      if (createForm.description.trim()) input.description = createForm.description.trim();
      const created = await createTradition(input);
      setTraditions(prev => [...prev, created]);
      setShowCreate(false);
      setCreateForm(EMPTY_FORM);
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create tradition");
    } finally {
      setCreateBusy(false);
    }
  }

  function startEditing(t: Tradition) {
    closeOverlays();
    setEditingSlug(t.slug);
    setEditForm({ name: t.name, origin: t.origin, era: t.era, description: t.description ?? "" });
    setEditError(null);
  }

  async function handleEditSubmit(e: FormEvent, slug: string) {
    e.preventDefault();
    const name = editForm.name.trim();
    const origin = editForm.origin.trim();
    const era = editForm.era.trim();
    if (!name || !origin || !era) return;

    setEditBusy(true);
    setEditError(null);
    try {
      const input: Partial<TraditionInput> = {
        name,
        origin,
        era,
        description: editForm.description.trim() || undefined,
      };
      const updated = await updateTradition(slug, input);
      setTraditions(prev => prev.map(t => (t.slug === slug ? updated : t)));
      setEditingSlug(null);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Failed to update tradition");
    } finally {
      setEditBusy(false);
    }
  }

  function handleDeleteClick(slug: string) {
    if (confirmingSlug !== slug) {
      setConfirmingSlug(slug);
      window.setTimeout(() => {
        setConfirmingSlug(prev => (prev === slug ? null : prev));
      }, 3000);
      return;
    }
    setConfirmingSlug(null);
    void performDelete(slug);
  }

  async function performDelete(slug: string) {
    try {
      await deleteTradition(slug);
    } catch {
      return;
    }
    setTraditions(prev => prev.filter(t => t.slug !== slug));
    setInfoSlug(prev => (prev === slug ? null : prev));
    setEditingSlug(prev => (prev === slug ? null : prev));
    if (selectedSlugs.has(slug)) {
      const next = new Set(selectedSlugs);
      next.delete(slug);
      const slugs = Array.from(next);
      setSelectedSlugs(next);
      startTransition(() => { updateTraditionPreferences(slugs); });
    }
  }

  function toggleInfo(slug: string) {
    if (infoSlug === slug) {
      setInfoSlug(null);
      return;
    }
    closeOverlays();
    setInfoSlug(slug);
  }

  return (
    <div className="flex h-screen bg-paper overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* header */}
        <div className="px-10 pt-7 pb-5 border-b border-line flex-shrink-0">
          <div className="font-mono text-[10px] text-muted uppercase tracking-widest">
            wisdom traditions
          </div>
          <div className="font-serif text-[36px] leading-tight mt-1">
            The voices in your room
          </div>
          <div className="text-[13px] text-muted mt-2 max-w-[540px] leading-relaxed">
            Soulra draws from these lineages when answering your questions. Pick three or more to
            keep in the room — you can always change them.
          </div>
        </div>

        {/* body */}
        <div className="flex-1 overflow-auto px-10 py-7">
          {/* active selection summary */}
          <div className="border-[1.5px] border-ink rounded-xl p-5 bg-paper-alt mb-7 flex items-start justify-between gap-6">
            <div className="flex-1">
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-3">
                your selection · {selectedSlugs.size} of {traditions.length} voices
              </div>
              <div className="flex flex-wrap gap-2">
                {selectedTraditions.map(t => (
                  <span key={t.slug} className="text-[11px] px-2.5 py-1 rounded-full bg-ink text-paper">
                    {t.name} ×
                  </span>
                ))}
              </div>
            </div>
            <div className="font-mono text-[10px] text-muted leading-relaxed text-right flex-shrink-0">
              {totalSources.toLocaleString()} source texts<br />
              {totalPassages.toLocaleString()} passages indexed
            </div>
          </div>

          {/* era filters + add control */}
          <div className="flex items-center gap-2 mb-6">
            <span className="font-mono text-[10px] text-muted self-center mr-1">filter:</span>
            {eras.map(era => (
              <Chip key={era} active={era === selectedEra} onClick={() => setSelectedEra(era)}>
                {era}
              </Chip>
            ))}
            <button
              type="button"
              onClick={toggleCreateForm}
              className="ml-auto font-mono text-[10px] uppercase tracking-widest text-muted hover:text-ink transition-colors underline underline-offset-4"
            >
              {showCreate ? "cancel" : "+ add tradition"}
            </button>
          </div>

          {/* create form */}
          {showCreate && (
            <form onSubmit={handleCreateSubmit} className="border-[1.5px] border-dashed border-ink rounded-xl p-5 mb-6 bg-paper-alt">
              <div className="font-mono text-[10px] text-muted uppercase tracking-widest mb-4">new tradition</div>
              <div className="grid grid-cols-3 gap-3 mb-3">
                <Field label="Name *">
                  <input
                    required
                    value={createForm.name}
                    onChange={e => setCreateForm(f => ({ ...f, name: e.target.value }))}
                    placeholder="e.g. Hermeticism"
                    className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
                  />
                </Field>
                <Field label="Origin *">
                  <input
                    required
                    value={createForm.origin}
                    onChange={e => setCreateForm(f => ({ ...f, origin: e.target.value }))}
                    placeholder="e.g. Egypt · ~200 CE"
                    className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
                  />
                </Field>
                <Field label="Era *">
                  <input
                    required
                    list="tradition-era-options"
                    value={createForm.era}
                    onChange={e => setCreateForm(f => ({ ...f, era: e.target.value }))}
                    placeholder="ancient, medieval…"
                    className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
                  />
                </Field>
              </div>
              <Field label="Description (optional)">
                <input
                  value={createForm.description}
                  onChange={e => setCreateForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Shown in the (i) info popover on the card"
                  className="w-full border border-line rounded-lg px-3 py-2 text-[13px] bg-paper focus:outline-none focus:border-ink"
                />
              </Field>
              <div className="flex items-center gap-3 mt-4">
                <button
                  type="submit"
                  disabled={createBusy}
                  className="font-mono text-[10px] uppercase tracking-widest px-4 py-2 rounded-lg bg-ink text-paper disabled:opacity-50"
                >
                  {createBusy ? "creating…" : "create tradition"}
                </button>
                {createForm.name.trim() && (
                  <span className="font-mono text-[10px] text-muted">slug will be: {slugify(createForm.name.trim())}</span>
                )}
              </div>
              {createError && <div className="font-mono text-[10px] text-red-600 mt-3">{createError}</div>}
            </form>
          )}

          <datalist id="tradition-era-options">
            {eras.filter(e => e !== "all").map(e => <option key={e} value={e} />)}
          </datalist>

          {/* tradition cards grid */}
          {visible.length === 0 ? (
            <div className="border border-dashed border-line rounded-xl p-10 text-center font-mono text-[11px] text-muted">
              {traditions.length === 0 ? "No traditions yet — add your first one above." : "No traditions in this era."}
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              {visible.map(t => {
                const isPicked = selectedSlugs.has(t.slug);

                if (editingSlug === t.slug) {
                  return (
                    <form
                      key={t.slug}
                      onSubmit={e => handleEditSubmit(e, t.slug)}
                      className="rounded-xl p-5 border-[1.5px] border-ink bg-paper"
                    >
                      <div className="font-mono text-[9px] text-muted uppercase tracking-widest mb-3">editing · {t.slug}</div>
                      <div className="space-y-2 mb-3">
                        <input
                          required
                          value={editForm.name}
                          onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                          placeholder="Name"
                          className="w-full border border-line rounded-lg px-2.5 py-1.5 text-[12px] bg-paper focus:outline-none focus:border-ink"
                        />
                        <input
                          required
                          value={editForm.origin}
                          onChange={e => setEditForm(f => ({ ...f, origin: e.target.value }))}
                          placeholder="Origin"
                          className="w-full border border-line rounded-lg px-2.5 py-1.5 text-[12px] bg-paper focus:outline-none focus:border-ink"
                        />
                        <input
                          required
                          list="tradition-era-options"
                          value={editForm.era}
                          onChange={e => setEditForm(f => ({ ...f, era: e.target.value }))}
                          placeholder="Era"
                          className="w-full border border-line rounded-lg px-2.5 py-1.5 text-[12px] bg-paper focus:outline-none focus:border-ink"
                        />
                        <input
                          value={editForm.description}
                          onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))}
                          placeholder="Description (optional)"
                          className="w-full border border-line rounded-lg px-2.5 py-1.5 text-[12px] bg-paper focus:outline-none focus:border-ink"
                        />
                      </div>
                      {editError && <div className="font-mono text-[9px] text-red-600 mb-2">{editError}</div>}
                      <div className="flex gap-2">
                        <button
                          type="submit"
                          disabled={editBusy}
                          className="font-mono text-[9px] uppercase tracking-widest px-3 py-1.5 rounded-lg bg-ink text-paper disabled:opacity-50"
                        >
                          {editBusy ? "saving…" : "save"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingSlug(null)}
                          className="font-mono text-[9px] uppercase tracking-widest px-3 py-1.5 rounded-lg border border-line text-muted"
                        >
                          cancel
                        </button>
                      </div>
                    </form>
                  );
                }

                return (
                  <div key={t.slug} className="relative group">
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => toggleTradition(t.slug)}
                      onKeyDown={e => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          toggleTradition(t.slug);
                        }
                      }}
                      className={`cursor-pointer rounded-xl p-5 transition-all ${
                        isPicked
                          ? "border-[1.5px] border-ink bg-ink text-paper shadow-md"
                          : "border border-line bg-paper hover:border-ink"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className={`font-serif text-[18px] font-medium ${isPicked ? "text-paper" : "text-ink"}`}>
                            {t.name}
                          </div>
                          <div className={`font-mono text-[9px] mt-1 tracking-wide ${isPicked ? "text-accent-soft" : "text-muted"}`}>
                            {t.origin}
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <button
                            type="button"
                            onClick={e => { e.stopPropagation(); toggleInfo(t.slug); }}
                            title="About this tradition"
                            className={`w-[15px] h-[15px] rounded-full border font-serif italic text-[9px] flex items-center justify-center leading-none ${
                              isPicked ? "border-accent-soft text-accent-soft" : "border-line text-muted hover:border-ink hover:text-ink"
                            }`}
                          >
                            i
                          </button>
                          <span className={`font-mono text-[13px] mt-0.5 ${isPicked ? "text-accent-soft" : "text-muted"}`}>
                            {isPicked ? "✓" : "+"}
                          </span>
                        </div>
                      </div>
                      <div className={`font-mono text-[10px] mt-3 pt-3 border-t ${isPicked ? "border-[#3a352d] text-accent-soft" : "border-dashed border-line text-muted"}`}>
                        {t.sources} sources &middot; {t.passages.toLocaleString()} passages
                      </div>
                    </div>

                    {infoSlug === t.slug && (
                      <div className="absolute top-12 right-4 w-[230px] rounded-lg bg-ink text-paper p-3 text-[10px] leading-relaxed shadow-lg z-10">
                        <div className="font-mono text-[8px] uppercase tracking-widest text-accent-soft mb-1.5">
                          about {t.name.toLowerCase()}
                        </div>
                        {t.description?.trim() ? t.description : "No description yet."}
                        <div className="mt-2 font-mono text-[9px] text-accent-soft">
                          slug: {t.slug} &middot; era: {t.era}
                        </div>
                      </div>
                    )}

                    <div className="absolute bottom-3 right-4 flex items-center gap-2.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        type="button"
                        onClick={e => { e.stopPropagation(); startEditing(t); }}
                        className={`font-mono text-[9px] uppercase tracking-widest ${isPicked ? "text-accent-soft hover:text-paper" : "text-muted hover:text-ink"}`}
                      >
                        edit
                      </button>
                      <button
                        type="button"
                        onClick={e => { e.stopPropagation(); handleDeleteClick(t.slug); }}
                        className={`font-mono text-[9px] uppercase tracking-widest ${
                          confirmingSlug === t.slug ? "text-red-600" : isPicked ? "text-accent-soft hover:text-paper" : "text-muted hover:text-ink"
                        }`}
                      >
                        {confirmingSlug === t.slug ? "confirm?" : "remove"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

Notes on what changed vs. the original and why:
- The card switched from `<button>` to `<div role="button" tabIndex={0}>` because it now contains a real `<button>` (the info icon) — a `<button>` cannot contain another interactive control without creating broken accessibility semantics. `onKeyDown` preserves keyboard activation (Enter/Space).
- Delete uses a 3-second timed "confirm?" state (`window.setTimeout`) rather than `onBlur`, since native button focus-on-click behavior is inconsistent across browsers and would make the confirm step unreliable.
- `eras` is computed as `["all", ...uniqueEras.sort()]` so "all" always stays first regardless of alphabetical sort of the rest.

- [ ] **Step 2: Verify the frontend compiles**

Run: `cd /Volumes/External/soulra && npx tsc --noEmit`
Expected: no type errors

- [ ] **Step 3: Manually verify in the browser — selection still works**

Open `http://localhost:3000/traditions`. Confirm: page loads without console errors, shows "No traditions yet — add your first one above." (since the DB was cleared in Task 4).

- [ ] **Step 4: Manually verify — create a tradition**

Click "+ add tradition", fill in Name "Hermeticism", Origin "Egypt · ~200 CE", Era "ancient", Description "A Greco-Egyptian tradition...". Confirm the "slug will be: hermeticism" preview appears as you type the name, and after submitting: the form collapses, the card appears in the grid, the era chip "ancient" appears in the filter row, and the selection summary shows "0 of 1 voices".

- [ ] **Step 5: Manually verify — select, edit, info popover, delete**

- Click the card to select it (turns dark, "✓" appears, summary updates to "1 of 1 voices" and shows a "Hermeticism ×" chip).
- Click the (i) icon — confirm a dark popover appears showing the description, slug, and era, and that clicking it does **not** also toggle selection.
- Hover the card, click "edit" — confirm an inline form appears pre-filled with the current values; change the Origin and click "save" — confirm the card returns to display mode with the new origin.
- Hover the card, click "remove" — confirm it becomes "confirm?"; click again — confirm the card disappears, the era chip list updates if it was the last tradition in that era, and the selection summary returns to "0 of 0 voices".

- [ ] **Step 6: Check the browser console for errors**

Confirm no "Cannot call startTransition while rendering" or other React warnings appear during any of the above interactions (this was the bug fixed earlier in this session — the rewrite must not reintroduce it).

- [ ] **Step 7: Commit**

```bash
cd /Volumes/External/soulra
git add components/screens/TraditionsClient.tsx
git commit -m "feat: let users create, edit, delete, and inspect their own traditions"
```

---

## Self-Review Checklist (for the plan author — already verified, recorded for traceability)

1. **Spec coverage** — every section of `docs/superpowers/specs/2026-06-07-traditions-crud-design.md` maps to a task:
   - §1 (remove seed data) → Task 4
   - §2 (CRUD endpoints + schemas) → Tasks 1–3 (POST + `_slugify` + `CreateTradition` already existed in the codebase and are documented as such, not re-implemented)
   - §3 (frontend API client) → Task 5
   - §4 (create form, inline edit, delete confirm, info popover, dynamic eras) → Task 6
   - §5 (error handling) → built into Task 6's `try/catch` + inline error state
   - §6 (testing) → Tasks 1–3 backend integration tests; Task 6 manual browser walkthrough (no frontend test infra exists in this repo)
2. **Placeholder scan** — no TBD/TODO/"add error handling"/"similar to above" — every step shows complete code or exact commands.
3. **Type consistency** — `TraditionInput` (Task 5) is used identically in `createTradition`, `updateTradition` (`Partial<TraditionInput>`), and `TraditionsClient.tsx`'s `handleCreateSubmit`/`handleEditSubmit`; `TraditionOut`/`TraditionUpdate` field names match between schema (Tasks 1–2) and the client interfaces.

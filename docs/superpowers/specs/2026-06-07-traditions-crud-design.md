# User-Managed Wisdom Traditions (CRUD)

**Date:** 2026-06-07
**Status:** Approved

## Problem

The 9 wisdom traditions shown on `/traditions` (Buddhism, Stoicism, Zen, etc.) are seeded into the database via migration `0002_traditions.py`. While the frontend itself reads them dynamically from `GET /api/v1/traditions`, the *data* is effectively a fixed starter set baked in at migration time — users have no way to add their own traditions, edit existing ones, or remove ones they don't want. The only mutation currently exposed is `PUT /traditions/preferences` (toggling which traditions are "selected").

Additionally, `TraditionsClient.tsx` hardcodes the era filter list:
```ts
const ERAS = ["all", "ancient", "medieval", "perennial"] as const;
```
This must come from the data, not a frontend constant.

## Approach

Make traditions a fully user-owned resource:
1. **Remove the seed data** from the migration — new installs start with an empty `traditions` table. Users build their list from scratch via the UI (confirmed with user: blank slate is the desired experience).
2. **Add full CRUD** to the backend: `POST`, `PUT /{slug}`, `DELETE /{slug}` alongside the existing `GET` and `PUT /preferences`.
3. **Manage everything inline on `/traditions`** — no new pages or routes. A "+ add tradition" control expands a create form; each card gets hover-revealed edit/delete/info affordances.
4. **Derive era filter chips from the live tradition list** — replace the hardcoded `ERAS` constant with a value computed from `traditions.map(t => t.era)`.
5. **Surface the existing `description` field** (already in the `Tradition` model, currently unused) via a small info-icon popover on each card.

---

## Section 1: Database & Migration

### Remove seed data

Edit `migrations/versions/0002_traditions.py` to stop inserting the 9 starter rows — keep only the `CREATE TABLE traditions` (and its `DROP TABLE` in `downgrade()`). The table ships empty; `GET /traditions` returns `{traditions: [], total_sources: 0, total_passages: 0}` until the user creates their own.

No model changes needed — `Tradition` (slug PK, name, origin, era, user_selected, description) already has every column the CRUD operations require.

---

## Section 2: Backend API — CRUD Endpoints

All added to `soulra/api/v1/traditions.py`. Route registration order matters: the literal `/traditions/preferences` path must stay registered **before** any `/traditions/{slug}` route so FastAPI matches the literal segment first.

### `POST /api/v1/traditions` — create

- Request body: `TraditionCreate { name: str, origin: str, era: str, description: str | None, slug: str | None }`
- If `slug` is omitted, derive it from `name` (lowercase, non-alphanumerics → `-`, collapse/trim dashes) — e.g. "Hermeticism" → `hermeticism`, "Christian Mystics" → `christian-mystics`.
- If the resulting slug already exists in the table → `409 Conflict` with a clear message ("A tradition with this slug already exists").
- New rows default `user_selected = False`.
- Returns `201` with `SuccessResponse[TraditionOut]` (sources/passages will be `0` until passages are ingested under that slug).

### `GET /api/v1/traditions/{slug}` — fetch one

- Returns `SuccessResponse[TraditionOut]`, `404` if not found. (Mainly for completeness/refresh-after-edit; the list endpoint remains the primary read path.)

### `PUT /api/v1/traditions/{slug}` — update

- Request body: `TraditionUpdate { name, origin, era, description }` — all optional, partial update (only provided fields change).
- `404` if the slug doesn't exist.
- Slug itself is immutable (it's the primary key and may be referenced by ingested passage metadata) — renaming is a `name` change, not a `slug` change.
- Returns `SuccessResponse[TraditionOut]` with the updated row (re-joined with live passage counts).

### `DELETE /api/v1/traditions/{slug}` — delete

- `404` if not found, otherwise `204`.
- No cascade — this only removes the catalog row. Any passages already ingested under that tradition slug remain in the vector store untouched (consistent with how `DELETE /passages/{id}` already behaves independently of the catalog). This is acceptable because re-creating a tradition with the same slug will cause its existing passages to reappear in counts.

### New/updated schemas (`soulra/schemas/tradition.py`)

```python
class TraditionCreate(BaseModel):
    name: str
    origin: str
    era: str
    description: str | None = None
    slug: str | None = None   # auto-derived from name when omitted

class TraditionUpdate(BaseModel):
    name: str | None = None
    origin: str | None = None
    era: str | None = None
    description: str | None = None
```

`TraditionOut` gains `description: str | None = None` so create/update responses (and the list/detail views) can round-trip it.

---

## Section 3: Frontend API Client (`lib/api.ts`)

Add three functions following the existing `listTraditions`/`updateTraditionPreferences` patterns (fetch against `${BASE}/api/v1/traditions...`, parse `SuccessResponse`, surface errors via thrown `Error` so the UI can display them):

```ts
export interface TraditionInput {
  name: string;
  origin: string;
  era: string;
  description?: string;
  slug?: string;
}

createTradition(input: TraditionInput): Promise<Tradition>
updateTradition(slug: string, input: Partial<TraditionInput>): Promise<Tradition>
deleteTradition(slug: string): Promise<void>
```

`Tradition` interface gains `description?: string`.

---

## Section 4: Frontend UI — `TraditionsClient.tsx`

Everything happens in place on `/traditions`; no new routes.

### State changes
- `traditions` becomes local state (seeded from `initialData.traditions`) so create/edit/delete can update it optimistically without a full page reload.
- `eras` is computed: `["all", ...new Set(traditions.map(t => t.era))].sort()` — replaces the hardcoded `ERAS` constant. New eras typed into the create/edit form automatically appear as filter chips once a tradition using them is saved.
- `total_sources`/`total_passages` summary numbers are recomputed from the live `traditions` array rather than read once from `initialData`.
- New local state: `showCreateForm`, create-form field values, `editingSlug` (which card, if any, is in inline-edit mode), loading/error flags for each async action.

### 1. Create — "+ add tradition"
- A small `+ add tradition` text control sits at the right edge of the era-filter row.
- Clicking it expands a dashed-border form card above the grid (matches the "selection summary" card styling) with: **Name**, **Origin**, **Era** (free-text input with a `<datalist>` suggesting existing eras — keeps it dynamic, not a hardcoded dropdown), **Description** (optional), and a live "slug will be: `…`" preview computed client-side with the same slugify rule as the backend.
- Submitting calls `createTradition`; on success the new tradition is appended to local state and the form collapses. On `409`/error, an inline message shows ("A tradition with this slug already exists").

### 2. Edit — hover (i)/✎/× row on each card
- Each tradition card's footer (currently just "`N sources · N passages`") gains hover-revealed icons: **✎ edit**, **× delete**, and an **(i) info** toggle (info detailed in #4).
- Clicking ✎ replaces that single card's content in-place with an inline edit form (Name/Origin/Era/Description fields pre-filled, Save/Cancel buttons) — same visual footprint as the card, only one card editable at a time (`editingSlug` guards this).
- Save calls `updateTradition(slug, …)`; on success the local `traditions` entry is replaced with the response and the card returns to display mode.

### 3. Delete — × on hover
- Clicking × calls `deleteTradition(slug)`; on success the card is removed from local state and, if it was selected, also removed from `selectedSlugs` (and a preference update is fired via the existing `startTransition(() => updateTraditionPreferences(...))` path so the backend stays in sync).
- Given this is destructive, show a lightweight inline confirm (e.g. the × becomes "confirm?" on first click, reverts after a few seconds or on second click elsewhere) rather than a blocking `window.confirm`.

### 4. Info — (i) popover
- A small circular `(i)` icon sits next to the `+`/`✓` selection indicator.
- Clicking toggles a dark popover (anchored bottom-right of the icon, matching the mockup shown to the user) displaying the tradition's `description` (falling back to "No description yet" if empty), plus `slug` and `era` for reference.
- Only one popover open at a time; clicking the icon again, clicking elsewhere, or selecting/editing/deleting closes it.
- This is purely a display affordance — it doesn't intercept the card's selection-toggle click (uses `stopPropagation` on the icon itself).

### Era filter chips
- Rendered from the computed `eras` array instead of the `ERAS` constant — otherwise unchanged (chip styling, `selectedEra` state, filtering logic all stay the same).

---

## Section 5: Error Handling

- All mutation calls (`createTradition`/`updateTradition`/`deleteTradition`) can fail (network, validation, conflict). Each surfaces its error inline near the relevant control (form error text for create/edit, a small toast-like message for delete) — no uncaught promise rejections, no blocking alerts.
- Backend returns standard `HTTPException` with descriptive `detail` messages (`409` for slug conflicts, `404` for missing slugs) that the frontend displays directly.

## Section 6: Testing

- Backend: extend the existing traditions test coverage (if any — verify during planning) with cases for create (including slug auto-derivation and conflict), update (partial updates, 404), and delete (204, 404, idempotent re-creation after delete).
- Frontend: manual verification in the browser per the golden path — create a tradition, see it appear and selectable, edit it, delete it, confirm era chips update dynamically, confirm info popover shows the description.

# Per-User Wisdom Libraries — Design

## Context

The wisdom corpus (vector store collection `wisdom_passages`, plus the `traditions`
table) is currently global: any chunk ever ingested, and any tradition ever
created, is visible to every user. There is one account in the dev DB
(`user_3F2yAzuFB9vdrwZIsPNtxMQQmVV`) which previously ingested ~1371 "mahabharat"
chunks. This design scopes both the embedded passages and the `traditions` table
per-user, so each user has their own personal wisdom library.

## 1. Data model changes

### `traditions` table

File: `soulra-backend/soulra/models/tradition.py`

- Add `user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)`.
- Change primary key from `slug` alone to composite `(user_id, slug)`. Two users
  may each have their own tradition with slug `"stoic"` without collision.

### Embedding metadata

The ingestion pipeline writes `cmetadata` per chunk
(`tradition`, `author`, `source`, `era`, `ingested_at`, `page`). Add a `user_id`
key to this dict so retrieval can filter by owner.

## 2. Propagation: user_id through the graph

`user_id` is threaded via `config["configurable"]["user_id"]` — the same
LangGraph `RunnableConfig` channel already used for `thread_id` and the
`usage_cb` callback, set once in `soulra/api/websocket.py`
(`config = {"configurable": {"thread_id": thread_id, "user_id": current_user.id}, "callbacks": [usage_cb]}`).

### `soulra/graph/nodes/intake.py`

- `get_tradition_options(user_id: str) -> list[str]` filters
  `select(Tradition.slug).where(Tradition.user_id == user_id)`.
- Falls back to `DEFAULT_TRADITION_OPTIONS` if the user has zero rows (cold
  start: a brand-new user gets generic routing categories; retrieval then
  yields no docs until they ingest content under one of those traditions,
  which naturally surfaces as `grade_result = "not_relevant"` and nudges them
  to ingest).
- `intake()` reads `user_id = config["configurable"]["user_id"]` and passes it
  to `get_tradition_options`.

### `soulra/graph/nodes/retrieve.py`

- `retrieve(state, config)` reads `user_id = config["configurable"]["user_id"]`
  and passes `user_id=user_id` to `retriever.search(...)`.

### `soulra/services/retrieval/retriever.py`

- `WisdomRetriever.search(query, tradition_filter=None, user_id=None, k=5)`
  builds the filter dict as `{"tradition": tradition_filter, "user_id": user_id}`
  (omitting keys that are `None`). `langchain_postgres`'s
  `_create_filter_clause` AND's multi-key filter dicts automatically, so this
  is additive — no new filter-combination logic needed.

## 3. Traditions API (`soulra/api/v1/traditions.py`)

All routes gain `current_user: User = Depends(get_current_user)`:

- `list_traditions` / `get_tradition`: filter `Tradition.user_id == current_user.id`.
- `create_tradition`: set `user_id = current_user.id` on the new row; the
  "already exists" conflict check becomes a lookup on
  `(current_user.id, slug)` instead of `slug` alone.
- `update_tradition` / `delete_tradition`: look up by
  `db.get(Tradition, (current_user.id, slug))`; 404 if the row doesn't belong
  to the caller (covers both "doesn't exist" and "belongs to someone else").
- `update_preferences`: only updates rows where `user_id == current_user.id`.
- `_passage_counts`: add `AND cmetadata->>'user_id' = :user_id` to `_COUNTS_SQL`,
  passing `current_user.id`.

## 4. Ingestion (`soulra/api/v1/ingest.py`, `soulra/tasks/ingest.py`)

Each `/ingest/pdf`, `/ingest/text`, `/ingest/url`, `/ingest/youtube` handler
already has `current_user` (via `get_current_user`). Add
`"user_id": current_user.id` to the `metadata` dict that's passed through
`_dispatch(...)` into the Celery task and on into
`IngestionPipeline.run(file, filename, metadata)`. The pipeline already spreads
`metadata` into each chunk's `cmetadata` via `_extract_documents` — no pipeline
code change needed beyond ensuring `user_id` is present in the incoming dict.

## 5. Migration & backfill

One Alembic migration (`soulra-backend/migrations/versions/`):

1. Add `traditions.user_id` as nullable `String(255)` with FK to `users.id`.
2. Backfill: `UPDATE traditions SET user_id = '<user_3F2yAzuFB9vdrwZIsPNtxMQQmVV>'`
   (the sole existing row, slug `mahabharat`).
3. Alter `traditions.user_id` to `NOT NULL`.
4. Drop the old single-column PK on `slug`, add composite PK `(user_id, slug)`.
5. Raw SQL: backfill existing embeddings —
   `UPDATE langchain_pg_embedding SET cmetadata = cmetadata || '{"user_id": "<user_3F2yAzuFB9vdrwZIsPNtxMQQmVV>"}'::jsonb WHERE cmetadata->>'tradition' = 'mahabharat'`
   (all 1371 existing rows).

The migration hardcodes the one known user_id as a one-time backfill for this
dev DB — acceptable since this is pre-launch dev data, not a general-purpose
multi-tenant migration script.

## 6. Testing

- `tests/unit/test_node_intake.py`: `get_tradition_options` test passes a
  `user_id` and asserts it's used in the query filter (mock
  `AsyncSessionLocal`/session.execute as already done).
- `tests/unit/test_node_retrieve_grade.py`: assert `retriever.search` is called
  with `user_id=...` from `config["configurable"]`.
- `tests/integration/test_traditions_api.py`: add a test creating the same
  slug under two different `user_id`s and asserting both succeed and each user
  only sees their own in `list_traditions`.
- Existing tests that call node functions directly continue to pass `{}` or a
  `{"configurable": {"user_id": "..."}}` config as needed.

## Out of scope

- No frontend changes are anticipated — the frontend already sends the Clerk
  session, and `get_current_user` already resolves `current_user.id` server-side.
- No changes to `SoulraState` (TypedDict) — `user_id` lives in `config`, not
  checkpointed state.

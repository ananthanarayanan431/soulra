# Authentication, Authorization, Admin Dashboard & Token Usage Limits

**Date:** 2026-06-10
**Status:** Approved

## Problem

Soulra currently has **no authentication or authorization at all**. Every API route is unauthenticated and unscoped — `conversations`, `journal`, `practice`, `ingest`, `traditions` have no concept of "owner". The frontend has no login/signup UI, no session handling, and no way to distinguish an admin from a regular user.

For production readiness we need:
1. Real user accounts (sign up / log in / log out), backed by a managed auth provider.
2. All user-owned data scoped to the authenticated user.
3. An admin role with a dedicated dashboard to view all users and login/session activity.
4. Per-user token usage accounting against an LLM call budget (default 1,000,000 tokens/user), enforced before new conversations start.

## Approach

Use **Clerk** as the managed auth provider:
- Next.js side: `@clerk/nextjs` middleware + prebuilt `<SignIn/>`/`<SignUp/>` components — minimal custom UI work, production-grade security (email verification, session management, MFA available) out of the box.
- FastAPI side: verify Clerk session JWTs via JWKS (`PyJWT` + `cryptography`), no DB coupling to Clerk required.
- Local `users` table mirrors Clerk users (lazy-synced on first authenticated request + via Clerk webhooks for profile/role changes), and is the source of truth for `role`, `token_limit`, `tokens_used`.
- **This phase ships against Clerk *test/placeholder* keys** (`pk_test_...` / `sk_test_...` env placeholders) — the user will create a real Clerk account and swap in real keys later. All Clerk integration code must work unchanged when real keys are substituted.

This is one cohesive change because auth, the admin dashboard, and token limits all share the same `users` table and the same auth dependency chain — splitting them would mean reworking the dependency wiring three times.

---

## Section 1: Database & Migrations

New Alembic migration `0006_users_auth.py` adds:

### `users`

| column | type | notes |
|---|---|---|
| `id` | `String` PK | Clerk user id (`user_xxx`), not a UUID |
| `email` | `String`, unique, indexed | |
| `name` | `String`, nullable | |
| `role` | `String`, default `"user"` | `"user"` \| `"admin"` |
| `token_limit` | `BigInteger`, default `1_000_000` | |
| `tokens_used` | `BigInteger`, default `0` | |
| `created_at` | `TIMESTAMP(tz)` | |
| `last_login_at` | `TIMESTAMP(tz)`, nullable | |

### `login_events`

| column | type | notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | FK → `users.id`, indexed | |
| `event_type` | `String` | `"login"` \| `"signup"` |
| `ip_address` | `String`, nullable | |
| `user_agent` | `String`, nullable | |
| `created_at` | `TIMESTAMP(tz)`, indexed | |

### `token_usage_log`

| column | type | notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | FK → `users.id`, indexed | |
| `conversation_id` | FK → `conversations.id`, nullable | |
| `model` | `String` | e.g. `anthropic/claude-sonnet-4-6` |
| `prompt_tokens` | `Integer` | |
| `completion_tokens` | `Integer` | |
| `total_tokens` | `Integer` | |
| `created_at` | `TIMESTAMP(tz)`, indexed | |

### Existing tables
Add `user_id: String, FK → users.id, nullable=False, indexed` to:
- `conversations`
- `journal_entries`
- `ingest_jobs`

Since there's no production data yet (early stage, confirmed blank-slate precedent from the traditions migration), these FKs are added as `NOT NULL` directly — no backfill migration needed.

---

## Section 2: Backend — Auth Dependencies & Middleware

New module `soulra/core/auth.py`:
- `verify_clerk_token(token: str) -> ClerkClaims` — fetches Clerk JWKS (cached), verifies signature/expiry/issuer, returns decoded claims (`sub`, `email`, etc.)
- `get_current_user(request, db) -> User` — FastAPI dependency:
  1. Extract `Authorization: Bearer <token>` header (401 if missing/invalid)
  2. Verify via `verify_clerk_token`
  3. Lazy-upsert local `users` row from claims (create on first sight with default role `"user"` and default `token_limit`)
  4. Update `last_login_at` and write a `login_events` row only if `last_login_at` is more than 30 minutes ago, to avoid logging an event on every request
  5. Return the `User` row
- `require_admin(user: User = Depends(get_current_user)) -> User` — raises `403` if `role != "admin"`

New config settings (`soulra/config.py`):
- `clerk_publishable_key: str` (placeholder default `pk_test_placeholder`)
- `clerk_secret_key: str` (placeholder default `sk_test_placeholder`)
- `clerk_jwks_url: str` (placeholder, e.g. `https://placeholder.clerk.accounts.dev/.well-known/jwks.json`)
- `clerk_webhook_secret: str` (placeholder)
- `default_token_limit: int = 1_000_000`

New webhook endpoint `soulra/api/v1/webhooks.py`:
- `POST /api/v1/webhooks/clerk` — Svix-signature-verified, handles `user.created`/`user.updated`/`user.deleted` to keep `users` table in sync (role changes made in Clerk dashboard propagate; role changes made in our admin UI are pushed to Clerk via API — see Section 4)

---

## Section 3: Backend — Token Usage Accounting & Limit Enforcement

### Capturing usage
LangChain's `ChatOpenAI` (via OpenRouter) populates `AIMessage.usage_metadata` (`input_tokens`, `output_tokens`, `total_tokens`) on each response. Each graph node that calls `fast_llm`/`smart_llm` (intake, rewrite, clarify, grade, rerank-adjacent, synthesize) already returns/produces an `AIMessage` or structured-output result that wraps one.

Add a small accumulator to `SoulraState`:
```python
token_usage: list[dict]  # [{"model": ..., "prompt_tokens": ..., "completion_tokens": ..., "total_tokens": ...}, ...]
```
Each node appends its usage entry (read from `result.usage_metadata` / `response_metadata["token_usage"]`) instead of discarding it.

### Persisting usage
At the end of a conversation (the `websocket.py` handler's "done" path, and the equivalent REST path in `conversations.py` if applicable):
1. Sum `state["token_usage"]` entries per model
2. Insert one `token_usage_log` row per model used
3. Increment `users.tokens_used` by the grand total (single `UPDATE ... SET tokens_used = tokens_used + :n`)

### Enforcement
Before starting a new conversation (REST endpoint that creates a conversation, and the WS `"start"` message handler):
- Load `current_user`, check `tokens_used < token_limit`
- If exceeded: REST → `403` with `ErrorResponse(code="TOKEN_LIMIT_EXCEEDED")`; WS → send `{"type": "error", "code": "TOKEN_LIMIT_EXCEEDED", "message": "..."}` and close

---

## Section 4: Backend — Admin API

New router `soulra/api/v1/admin.py`, prefix `/api/v1/admin`, all routes behind `require_admin`:

- `GET /admin/users?limit=&offset=&search=` — paginated list: `id, email, name, role, token_limit, tokens_used, created_at, last_login_at`
- `GET /admin/users/{user_id}` — single user detail incl. recent `login_events` and `token_usage_log` summary
- `PATCH /admin/users/{user_id}` — body `{role?, token_limit?}`. Role changes also call Clerk's Backend API (`PATCH /users/{id}/metadata`) to keep `publicMetadata.role` in sync (no-op / logged warning if Clerk call fails with placeholder keys)
- `GET /admin/login-events?user_id=&limit=&offset=` — paginated login activity, optionally filtered by user
- `GET /admin/usage?user_id=&limit=&offset=` — paginated token usage log, optionally filtered by user

All admin mutations are written to the existing structured logger (`structlog`) with actor id, target id, and change — no new audit table needed at this stage.

---

## Section 5: Backend — Scoping Existing Routes

`conversations.py`, `journal.py`, `practice.py`, `ingest.py`: add `current_user: User = Depends(get_current_user)` to every route, filter/insert with `user_id = current_user.id`. Attempting to access another user's resource by id → `404` (not `403`, to avoid leaking existence).

`traditions.py` and `passages.py` remain global/shared (traditions are not currently per-user — out of scope for this change; confirmed by existing schema with no user concept).

---

## Section 6: Frontend — Clerk Integration

- Add `@clerk/nextjs` dependency
- `app/layout.tsx`: wrap in `<ClerkProvider>`
- `middleware.ts` at project root: `clerkMiddleware()` protecting every route except `/`, `/sign-in`, `/sign-up`, and Next static/image assets. All app routes (`/home`, `/chat`, `/journal`, `/daily`, `/traditions`, `/ingest`, `/admin`, etc.) require a signed-in session and redirect to `/sign-in` otherwise.
- New routes `app/sign-in/[[...sign-in]]/page.tsx` and `app/sign-up/[[...sign-up]]/page.tsx` rendering Clerk's `<SignIn/>`/`<SignUp/>`
- `lib/api.ts` and `lib/ws.ts`: every call attaches `Authorization: Bearer <token>` using `auth().getToken()` (server components/route handlers) or `useAuth().getToken()` (client components)
- Env additions to `.env.local`: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` (placeholder test values)

---

## Section 7: Frontend — Admin Dashboard

New route group `app/admin/`:
- `app/admin/layout.tsx` — server-side check: fetch current user via backend (`/api/v1/admin/users/{me}` or a lightweight `/api/v1/me`), redirect to `/home` if `role !== "admin"`
- `app/admin/users/page.tsx` — table: email, name, role, joined, last login, tokens used / limit (progress bar), inline editable `token_limit`, role toggle (user ⇄ admin)
- `app/admin/activity/page.tsx` — paginated login activity table: user email, event type, IP, user agent, timestamp; filter by user
- `app/admin/usage/page.tsx` — paginated token usage log: user email, model, tokens (prompt/completion/total), timestamp; filter by user

A small "Admin" link appears in the main nav (`components/layout`) only when `role === "admin"` (read from a `/api/v1/me` endpoint added alongside the admin API).

New endpoint: `GET /api/v1/me` — returns the current user's own profile (id, email, name, role, token_limit, tokens_used) — used by both the nav-link visibility check and any future account page.

---

## Section 8: Production-readiness items included

- All new secrets (Clerk keys, webhook secret) via env vars with placeholder defaults, `.env.example` updated
- Rate limiting on `/api/v1/webhooks/clerk` and auth-sensitive endpoints not otherwise covered (lightweight, e.g. `slowapi`) — only if it doesn't add significant complexity; otherwise deferred and noted as follow-up
- Structured logging (existing `structlog`) for all admin actions and auth failures
- New tests: unit tests for `verify_clerk_token`/`get_current_user`/`require_admin` (mocking JWKS), integration tests for admin endpoints (admin vs non-admin), token-limit enforcement test, scoping tests (user A cannot see user B's conversations)

---

## Out of scope / explicitly deferred

- Real Clerk account/keys (user will provision and swap in)
- Social login providers, MFA configuration (Clerk dashboard config, no code changes needed)
- Per-tradition or per-passage user ownership
- Billing/payment for token top-ups
- A full security audit of unrelated existing code (ingestion pipeline, retrieval, etc.) — this change focuses on the auth/admin/limits subsystem and its direct touchpoints

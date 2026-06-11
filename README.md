# Soulra

Soulra is an AI wisdom companion web app — a Next.js frontend paired with a FastAPI backend for chat, journaling, and tradition-based guidance.

## Project structure

- `app/`, `components/`, `hooks/`, `lib/` — Next.js (App Router) frontend
- `soulra-backend/` — FastAPI backend, Celery workers, and database migrations

## Architecture

**Stack:** Next.js (App Router) + FastAPI + PostgreSQL/pgvector + Redis/Celery + Clerk (auth) + LangGraph (agentic reasoning).

### Frontend (`app/`)

- `home`, `chat`, `journal`, `daily`, `traditions`, `ingest`, `admin/*` — main app routes
- `lib/api.ts` / `lib/api-fetch.ts` — REST client that attaches a Clerk bearer token to requests against the backend's `/api/v1/*` endpoints
- `hooks/useSoulraChat.ts` — WebSocket hook driving the real-time chat state machine (connecting → thinking → clarifying → responding → done)
- `proxy.ts` — Clerk middleware protecting all routes except `/`, `/sign-in/*`, `/sign-up/*`

### Backend (`soulra-backend/soulra/`)

- `api/v1/` — REST endpoints: `conversations`, `journal`, `traditions`, `practice`, `ingest`, `admin`, `me`, `health`
- `api/websocket.py` — `/ws/chat` endpoint that runs the LangGraph conversation flow and streams status/clarify/tradition/action-step events
- `graph/` — LangGraph agent: intake → vector retrieval → Cohere rerank → grade → clarify (if needed) → synthesize → emit tradition cards + action steps
- `models/` — SQLAlchemy models: User, Conversation, JournalEntry, Tradition, PracticeArc/Day, IngestJob, LoginEvent, TokenUsageLog
- `services/` — business logic: `ingestion/` (PDF parsing, chunking, embeddings), `retrieval/retriever.py` (pgvector search), `llm/factory.py` (Claude/Cohere clients), `token_usage.py`, `cache.py` (Redis), `practice_builder.py`
- `tasks/ingest.py` — Celery task that processes uploaded sources (PDF/URL/text/YouTube) into embedded passages
- `core/auth.py` — verifies Clerk JWTs (JWKS) and gets-or-creates the User record on first login

### Data flow

- **Chat**: client opens an authenticated WebSocket → backend runs the LangGraph flow, streams events back, and persists the Conversation, generated Practice arc, and token usage
- **Journal**: CRUD entries linked to conversations/traditions, with tagging, "apply wisdom" tracking, and revisit suggestions
- **Ingest**: client uploads a source → staged in Redis → Celery worker chunks/embeds it into pgvector → frontend polls job status until done

### Infrastructure

- `docker-compose.yml` (in `soulra-backend/`) runs Postgres (pgvector), Redis, the FastAPI backend, and a Celery worker on the `ingest` queue
- Alembic migrations in `soulra-backend/migrations/` run automatically on backend startup

## Frontend

Requirements: Node.js 20+

```bash
npm install
npm run dev        # start dev server (http://localhost:3000)
npm run lint        # run eslint
npm run typecheck   # run tsc --noEmit
npm run build       # production build
```

Authentication is handled via Clerk — see `docs/` for required environment variables.

## Backend

Requirements: Python 3.12+, Docker (for Postgres + Redis)

```bash
cd soulra-backend
cp .env.example .env     # fill in DATABASE_URL and OPENROUTER_API_KEY
make install              # create .venv and install dependencies
make infra-up             # start postgres + redis via Docker
make server                # run FastAPI dev server
make worker                # run Celery worker (separate terminal)
make test                  # run test suite
```

Other useful targets: `make lint`, `make fmt`, `make typecheck`. See `soulra-backend/Makefile` for the full list.

## Notes

- This repo's Next.js version has breaking changes from upstream — see [AGENTS.md](AGENTS.md) before writing frontend code.

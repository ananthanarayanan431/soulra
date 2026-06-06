# Soulra Backend – developer convenience targets
# Requires Python 3.12+ (https://www.python.org/downloads/)

VENV          := .venv
SYSTEM_PYTHON ?= python3
PYTHON        := $(VENV)/bin/python
PIP           := $(VENV)/bin/pip
PYTEST        := $(VENV)/bin/pytest
RUFF          := $(VENV)/bin/ruff
MYPY          := $(VENV)/bin/mypy
UVICORN       := $(VENV)/bin/uvicorn
CELERY        := $(VENV)/bin/celery

# ── Setup ────────────────────────────────────────────────────────────────────

.PHONY: venv
venv:
	$(SYSTEM_PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

.PHONY: install
install: venv
	$(PIP) install -e ".[dev]"

# ── Lint / type-check ─────────────────────────────────────────────────────────

.PHONY: lint
lint:
	$(RUFF) check .
	$(RUFF) format --check .

.PHONY: fmt
fmt:
	$(RUFF) format .
	$(RUFF) check --fix .

.PHONY: typecheck
typecheck:
	$(MYPY) soulra/ --ignore-missing-imports

# ── Tests ─────────────────────────────────────────────────────────────────────

.PHONY: test
test:
	$(PYTEST) tests/ -v

.PHONY: test-unit
test-unit:
	$(PYTEST) tests/unit/ -v

# ── Clean ─────────────────────────────────────────────────────────────────────

.PHONY: clean
clean:
	rm -rf $(VENV) __pycache__ .pytest_cache

# ── Infrastructure ────────────────────────────────────────────────────────────

.PHONY: infra-up
infra-up:
	docker compose up -d postgres redis

.PHONY: infra-down
infra-down:
	docker compose down

# ── Server ────────────────────────────────────────────────────────────────────

.PHONY: server
server:
	$(UVICORN) soulra.main:app --reload --host 0.0.0.0 --port 8000

# ── Worker ────────────────────────────────────────────────────────────────────

.PHONY: worker
worker:
	$(CELERY) -A soulra.celery_app worker \
		--loglevel=info \
		--queues=ingest \
		--concurrency=2 \
		--max-tasks-per-child=50

# ── Quick start ───────────────────────────────────────────────────────────────
# New developer onboarding:
#   1. cp .env.example .env        # fill in DATABASE_URL and OPENROUTER_API_KEY
#   2. make install                # create .venv and install all deps
#   3. make infra-up               # start postgres + redis via Docker
#   4. make server                 # run FastAPI dev server (separate terminal)
#   5. make worker                 # run Celery worker (separate terminal)
#   6. make test                   # run test suite

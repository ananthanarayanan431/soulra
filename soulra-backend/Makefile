# Soulra Backend – developer convenience targets
# Requires Python 3.12+ (https://www.python.org/downloads/)

VENV          := .venv
SYSTEM_PYTHON ?= python3
PYTHON        := $(VENV)/bin/python
PIP           := $(VENV)/bin/pip
PYTEST        := $(VENV)/bin/pytest
RUFF          := $(VENV)/bin/ruff
MYPY          := $(VENV)/bin/mypy

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

# ── Quick start ───────────────────────────────────────────────────────────────
# New developer onboarding:
#   1. cp .env.example .env        # fill in DATABASE_URL and OPENROUTER_API_KEY
#   2. make install                # create .venv and install all deps
#   3. make test                   # run test suite

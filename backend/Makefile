# Soulra Backend – developer convenience targets
# Requires Python 3.12+ (https://www.python.org/downloads/)

VENV   := .venv
PYTHON := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

# ── Setup ────────────────────────────────────────────────────────────────────

.PHONY: venv
venv:
	python3.12 -m venv $(VENV)
	$(PIP) install --upgrade pip

.PHONY: install
install: venv
	$(PIP) install -e ".[dev]"

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

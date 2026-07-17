# Stamp file: uv sync runs only when pyproject.toml changes.
STAMP := .venv/.install-stamp

.PHONY: all check install format lint lint-fix typecheck test test-fast \
        test-unit test-integration test-system coverage clean upload sync-skills

PYPI_NAME := frob
SRC       := src
TESTS     := tests

# ---------- default ----------

# Runs each tool exactly once: format, lint, typecheck, test.
all: $(STAMP)
	uv run black $(SRC)/ $(TESTS)/
	uv run ruff check $(SRC)/ $(TESTS)/ --fix --select I
	uv run ruff format $(SRC)/ $(TESTS)/
	uv run ty check $(SRC)/
	uv run pytest $(TESTS)/ -q -n auto

# Read-only gate (no auto-fix). Safe to run in CI.
check: $(STAMP)
	uv run frob check

coverage: $(STAMP)
	uv run pytest --cov=src/frob --cov-branch --cov-report=xml -q
	uv run frob check --stamp-coverage

# ---------- install (stamp-guarded) ----------

$(STAMP): pyproject.toml
	uv sync --all-extras
	@touch $(STAMP)

install: $(STAMP)

# ---------- formatting & linting ----------

format: $(STAMP)
	uv run black $(SRC)/ $(TESTS)/
	uv run ruff check $(SRC)/ $(TESTS)/ --fix --select I
	uv run ruff format $(SRC)/ $(TESTS)/

lint: $(STAMP)
	uv run ruff check $(SRC)/ $(TESTS)/
	uv run ty check $(SRC)/

lint-fix: $(STAMP)
	uv run ruff check $(SRC)/ $(TESTS)/ --fix
	uv run black $(SRC)/ $(TESTS)/
	uv run ruff format $(SRC)/ $(TESTS)/

typecheck: $(STAMP)
	uv run ty check $(SRC)/

# ---------- tests ----------

test: $(STAMP)
	uv run pytest $(TESTS)/ -q -n auto

test-fast: $(STAMP)
	uv run pytest $(TESTS)/ -q --testmon

test-unit: $(STAMP)
	uv run pytest $(TESTS)/unit/ -q -n auto

test-integration: $(STAMP)
	uv run pytest $(TESTS)/integration/ -q

test-system: $(STAMP)
	uv run pytest $(TESTS)/system/ -q -n auto

# ---------- skills / agents sync ----------
# Full bidirectional sync: creates new entries, updates existing ones, and
# removes stale entries from ~/.claude that no longer exist here.

CLAUDE_DIR := $(HOME)/.claude

sync-skills:
	@mkdir -p "$(CLAUDE_DIR)/agents" "$(CLAUDE_DIR)/skills"
	@echo "--- syncing agents ---"
	@for d in agents/*/; do \
	    name=$$(basename "$$d"); \
	    mkdir -p "$(CLAUDE_DIR)/agents/$$name"; \
	    cp -r "$$d"* "$(CLAUDE_DIR)/agents/$$name/"; \
	    echo "  synced agent: $$name"; \
	done
	@echo "--- syncing skills ---"
	@for d in skills/*/; do \
	    name=$$(basename "$$d"); \
	    mkdir -p "$(CLAUDE_DIR)/skills/$$name"; \
	    cp -r "$$d"* "$(CLAUDE_DIR)/skills/$$name/"; \
	    echo "  synced skill: $$name"; \
	done
	@echo "--- removing stale agents ---"
	@for d in "$(CLAUDE_DIR)/agents/"/*/; do \
	    [ -d "$$d" ] || continue; \
	    name=$$(basename "$$d"); \
	    if [ ! -d "agents/$$name" ]; then \
	        rm -rf "$$d"; \
	        echo "  removed stale agent: $$name"; \
	    fi; \
	done
	@echo "--- removing stale skills ---"
	@for d in "$(CLAUDE_DIR)/skills/"/*/; do \
	    [ -d "$$d" ] || continue; \
	    name=$$(basename "$$d"); \
	    if [ ! -d "skills/$$name" ]; then \
	        rm -rf "$$d"; \
	        echo "  removed stale skill: $$name"; \
	    fi; \
	done
	@echo "done."

# ---------- build & publish ----------

clean:
	rm -rf dist/ build/ .pytest_cache/ .ruff_cache/ .testmondata
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null; true

upload: clean
	@set -a && . ./.env && set +a; \
	NEW=$$(uv run python scripts/bump_version.py); \
	git add pyproject.toml; \
	git commit -m "chore: bump version to $$NEW"; \
	git push; \
	uv build && uv publish

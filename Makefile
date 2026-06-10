.PHONY: all install build lint lint-fix format typecheck test test-fast test-unit \
        test-integration test-system clean upload sync-skills check

PYPI_NAME := frob
SRC       := src
TESTS     := tests

# ---------- default ----------

# Run everything: format, lint, typecheck, then full test suite.
all: format lint typecheck test

# Verify everything is green without modifying files (CI-style gate).
check: lint typecheck test

# ---------- install ----------

install:
	uv sync --all-extras

# ---------- formatting & linting ----------

format: install
	uv run black $(SRC)/ $(TESTS)/
	uv run ruff check $(SRC)/ $(TESTS)/ --fix --select I
	uv run ruff format $(SRC)/ $(TESTS)/

lint: install
	uv run ruff check $(SRC)/ $(TESTS)/
	uv run ty check $(SRC)/

lint-fix: install
	uv run ruff check $(SRC)/ $(TESTS)/ --fix
	uv run black $(SRC)/ $(TESTS)/
	uv run ruff format $(SRC)/ $(TESTS)/

typecheck: install
	uv run ty check $(SRC)/

# ---------- tests ----------

# Full suite: unit + integration + system
test: install
	uv run pytest $(TESTS)/ -q

# Fast incremental: only tests touching changed files
test-fast: install
	uv run pytest $(TESTS)/ -q --testmon

# Unit tests only (fast, no subprocess)
test-unit: install
	uv run pytest $(TESTS)/unit/ -q

# Integration tests: cross-module API interactions
test-integration: install
	uv run pytest $(TESTS)/integration/ -q

# System / e2e tests: real CLI via subprocess
test-system: install
	uv run pytest $(TESTS)/system/ -q

# ---------- skills / agents sync ----------
# Copies skills and agents that already exist in ~/.claude to their counterparts
# here. Only updates entries whose names match; never creates new ones.

CLAUDE_DIR := $(HOME)/.claude

sync-skills:
	@for d in skills/*/; do \
	    name=$$(basename "$$d"); \
	    target="$(CLAUDE_DIR)/skills/$$name"; \
	    if [ -d "$$target" ]; then \
	        cp -r "$$d"* "$$target/"; \
	        echo "synced skill: $$name -> $$target"; \
	    fi; \
	done
	@for d in agents/*/; do \
	    name=$$(basename "$$d"); \
	    target="$(CLAUDE_DIR)/agents/$$name"; \
	    if [ -d "$$target" ]; then \
	        cp -r "$$d"* "$$target/"; \
	        echo "synced agent: $$name -> $$target"; \
	    fi; \
	done

# ---------- build & publish ----------

clean:
	rm -rf dist/ build/ .pytest_cache/ .ruff_cache/ .testmondata
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null; true

upload: clean
	@LOCAL=$$(python -c "import tomllib; t=tomllib.load(open('pyproject.toml','rb')); print(t['project']['version'])"); \
	PYPI=$$(curl -s https://pypi.org/pypi/$(PYPI_NAME)/json 2>/dev/null \
	        | python -c "import sys,json; print(json.load(sys.stdin)['info']['version'])" 2>/dev/null \
	        || echo "0.0.0"); \
	BUMP=$$(python -c " \
	from packaging.version import Version; \
	l, p = Version('$$LOCAL'), Version('$$PYPI'); \
	print('yes' if l <= p else 'no')"); \
	if [ "$$BUMP" = "yes" ]; then \
	    NEW=$$(python -c " \
	v = '$$LOCAL'.split('.'); v[-1] = str(int(v[-1])+1); print('.'.join(v))"); \
	    python -c " \
	import re, pathlib; \
	p = pathlib.Path('pyproject.toml'); \
	p.write_text(re.sub(r'^version = .+', 'version = \"$$NEW\"', p.read_text(), flags=re.M))"; \
	    echo "Bumped $$LOCAL -> $$NEW"; \
	    git add pyproject.toml; \
	    git commit -m "chore: bump version to $$NEW"; \
	    git push; \
	fi; \
	uv build && uv publish

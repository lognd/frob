# Stamp file: uv sync runs only when pyproject.toml changes.
STAMP := .venv/.install-stamp

.PHONY: all check install format lint lint-fix typecheck test test-fast \
        test-unit test-integration test-system clean upload sync-skills

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
	uv run ruff check $(SRC)/ $(TESTS)/
	uv run ty check $(SRC)/
	uv run pytest $(TESTS)/ -q -n auto

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

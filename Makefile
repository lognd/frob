# Stamp file: uv sync runs only when pyproject.toml changes.
STAMP := .venv/.install-stamp

.PHONY: all check install install-tool core format lint lint-fix typecheck test test-fast \
        test-unit test-integration test-system coverage coverage-fast clean upload \
        sync-skills playbook deploy-audit

PYPI_NAME := frob
SRC       := src
TESTS     := tests

# ---------- default ----------

# Runs each tool exactly once: format, lint, typecheck, test.
all: $(STAMP)
	uv run ruff check $(SRC)/ $(TESTS)/ --fix --select I
	uv run ruff format $(SRC)/ $(TESTS)/
	uv run ty check $(SRC)/
	uv run pytest $(TESTS)/ -q -n auto

# Read-only gate (no auto-fix). Safe to run in CI.
# T-0248: fail loudly, before frob check even runs, if strata-core/frob-core
# source outpaces the built native extension -- otherwise frob check/frob
# test silently run against the stale native and give wrong results (the
# T-0166 review incident).
check: $(STAMP)
	uv run python -c "from pathlib import Path; from frob.strata._native_staleness import check_native_staleness_or_exit; check_native_staleness_or_exit(Path('.'))"
	uv run frob check

# Prints the agent playbook (per-dispatch checklist: worktree warm-up,
# scope/evidence/gate discipline). Every worktree agent should read this
# before starting a ticket -- see CLAUDE.md.
playbook:
	@cat docs/guides/agent-playbook.md

# T-0464: subprocess coverage must be explicitly enabled or it silently
# doesn't happen. Most frob code is exercised only via CLI subprocess
# system tests (tests/system/conftest.py spawns `python -m frob`); a bare
# `pytest --cov` only measures the main pytest process, so everything a
# subprocess test covers reads as 0% hit and coverage.xml comes out
# deflated (observed line-rate 0.49 vs a real 0.87), which explodes TEST005
# into hundreds of false per-symbol/per-module coverage-floor findings.
# COVERAGE_PROCESS_START must be ABSOLUTE ($(CURDIR)/pyproject.toml): the
# .pth hook resolves it against each subprocess's OWN cwd, and subprocess
# tests run in tmp_path, so a relative value makes coverage raise
# ConfigError on stderr -- both losing that subprocess's coverage and
# breaking tests that assert the child's stderr is empty.
# COVERAGE_PROCESS_START + [tool.coverage.run] parallel=true
# (pyproject.toml) makes every subprocess (via the coverage-installed .pth
# site hook) write its own `.coverage.*` data file; `coverage combine`
# merges them all before the xml report is generated, so `frob check
# --stamp-coverage` stamps and TEST005 evaluates against real coverage.
# NOTE: do NOT also pin COVERAGE_FILE here to corral the subprocess data
# files. It is inherited by nested projects too -- the scaffold DX tests
# build a demo project and run ITS coverage, and a global COVERAGE_FILE
# redirects that statement-only data into frob's branch-mode file, which
# makes `combine` fail with "Can't combine branch coverage data with
# statement data". Fixture repos instead gitignore the stray `.coverage.*`
# locally, the same way they gitignore `.frob/`.
coverage: $(STAMP)
	rm -f .coverage .coverage.*
	COVERAGE_PROCESS_START=$(CURDIR)/pyproject.toml uv run pytest --cov=src/frob --cov-branch --cov-report= -q
	uv run coverage combine
	uv run coverage xml
	uv run frob check --stamp-coverage
	uv run frob clean -y

# T-0484: incremental coverage for the common "one small change" loop --
# `make coverage` above always re-runs the WHOLE suite under coverage, so
# TEST005/TEST006 feedback costs a full-suite wait even for a one-line
# edit. This restricts the pytest run to the touched set's own selected
# python targets (frob.testing.python_coverage_targets -- the SAME
# selection algorithm `frob test --base` already runs and already trusts,
# not a second hand-written diff-to-tests mapping) and APPENDS onto the
# existing `.coverage` data (no `rm -f .coverage` first) instead of
# starting from zero: every file the touched-set run does not re-execute
# keeps its prior run's hit data, valid precisely because that file's
# source has not changed since the last full/incremental run measured it.
# BASE defaults to main; override with `make coverage-fast BASE=<ref>`.
# Falls back to a full `make coverage` when there is no `.coverage` data
# yet to append onto (first run always needs the full baseline) OR the
# touched set selects nothing (an untracked/target-less diff, e.g. a
# docs-only change) -- coverage-fast in that case has nothing incremental
# to do and stamping cheaply refreshes file hashes against the unchanged
# coverage.xml, which is what `frob check --stamp-coverage` alone would
# already require regardless.
#
# NOT built here (disclosed, not silently dropped -- see T-0484's Done
# report): a background/daemon-side refresh (the ticket's option (a)) and
# non-python touched-set coverage (rust/strata are still measured only by
# the full `make coverage` run) -- both are separately-scoped follow-ups.
BASE ?= main
coverage-fast: $(STAMP)
	@if [ ! -f .coverage ]; then \
		echo "coverage-fast: no prior .coverage data to append onto -- running full make coverage"; \
		$(MAKE) coverage; \
	else \
		targets="$$(uv run python -c "from pathlib import Path; from frob.graph import build_graph, load_graph; from frob.testing import python_coverage_targets; root = Path('.'); cache = root / '.frob' / 'cache.db'; loaded = load_graph(cache); snap = (loaded if loaded.is_ok else build_graph(root, cache)).danger_ok; print('\n'.join(t for t in python_coverage_targets(root, snap, '$(BASE)') if t != '*'))" 2>/dev/null)"; \
		if [ -z "$$targets" ]; then \
			echo "coverage-fast: touched set selects no python target against $(BASE) -- nothing incremental to run"; \
		else \
			echo "$$targets" | COVERAGE_PROCESS_START=$(CURDIR)/pyproject.toml xargs uv run pytest --cov=src/frob --cov-branch --cov-append --cov-report= -q; \
		fi; \
		uv run coverage combine --append 2>/dev/null || uv run coverage combine; \
		uv run coverage xml; \
		uv run frob check --stamp-coverage; \
	fi

# VirtualBox snapshot-diff harness proving artifact-free install/uninstall
# (T-0259, deploy epic T-0254 child 5). NOT part of `check`/`all` -- it
# needs a real VBoxManage guest (FROB_VM/FROB_VM_SSH_HOST/FROB_VM_SSH_KEY
# env vars, or pass args directly: `make deploy-audit ARGS="--vm ... "`).
# Degrades to a clear SKIPPED (exit 2) when VBoxManage is not installed.
deploy-audit: $(STAMP)
	uv run frob deploy audit \
		--vm "$${FROB_VM:?set FROB_VM or pass --vm via ARGS}" \
		--ssh-host "$${FROB_VM_SSH_HOST:?set FROB_VM_SSH_HOST}" \
		--ssh-key "$${FROB_VM_SSH_KEY:?set FROB_VM_SSH_KEY}" \
		$(ARGS)

# ---------- install (stamp-guarded) ----------

# The `smt` extra (z3-solver) is opt-in and ships no wheel for some
# platforms (e.g. aarch64), where it fails to build from source; R7 degrades
# honestly without it. Sync only the routinely-buildable extras so a missing
# z3 wheel never bricks the dev environment. Install SMT support explicitly
# with `uv pip install "frob[smt]"` on platforms where z3 is available.
$(STAMP): pyproject.toml
	uv sync --extra serve
	@touch $(STAMP)

install: $(STAMP) core

# ---------- native extension (frob-core, Rust/PyO3) ----------

# Build and install the frob-core native extension into the venv. The
# smart-dup R3+ rungs need it; R1/R2 and every other feature work without
# it, so this is a best-effort step that warns rather than fails when the
# Rust toolchain is absent.
core: $(STAMP)
	@command -v cargo >/dev/null 2>&1 || { \
		echo "cargo not found; skipping frob-core (smart-dup R3+ disabled)"; \
		exit 0; }
	VIRTUAL_ENV=$(CURDIR)/.venv uvx maturin develop --uv --release -m frob-core/Cargo.toml
	VIRTUAL_ENV=$(CURDIR)/.venv uvx maturin develop --uv --release -m strata-core/Cargo.toml

# ---------- standalone tool install (T-0133) ----------

# `uv tool install frob` alone installs only the pure-Python `frob` package
# -- neither native extension (frob-core, strata-core) is a declared
# dependency (they are local maturin path packages, not published wheels;
# see pyproject.toml's dependencies list and T-0133's Done report for why
# a real `[project.optional-dependencies]` extra can't point at them). That
# leaves the standalone binary working (frob.lang degrades every .strata
# file to a typed Err and frob-core-only dup rungs turn off, per T-0133's
# (a) decision) but short of full functionality. This target rebuilds and
# installs both native extensions as `--with` deps of the same `uv tool`
# environment so the globally-installed `frob` gets them too. Requires a
# Rust toolchain (`cargo`); true wheel publishing to PyPI for frob-core/
# strata-core is out of scope for this ticket -- see docs/guides/install.md.
install-tool:
	uv tool install --force --reinstall . --with ./strata-core --with ./frob-core --with "mcp>=1.28.1"

# ---------- formatting & linting ----------

format: $(STAMP)
	uv run ruff check $(SRC)/ $(TESTS)/ --fix --select I
	uv run ruff format $(SRC)/ $(TESTS)/

lint: $(STAMP)
	uv run ruff check $(SRC)/ $(TESTS)/
	uv run ty check $(SRC)/

lint-fix: $(STAMP)
	uv run ruff check $(SRC)/ $(TESTS)/ --fix
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

clean: $(STAMP)
	uv run frob clean --all -y
	rm -f .testmondata

upload: clean
	@set -a && . ./.env && set +a; \
	NEW=$$(uv run python scripts/bump_version.py); \
	git add pyproject.toml; \
	git commit -m "chore: bump version to $$NEW"; \
	git push; \
	uv build && uv publish

# Stamp file: uv sync runs only when pyproject.toml changes.
STAMP := .venv/.install-stamp

.PHONY: all check install install-tool core format lint lint-fix typecheck test test-fast \
        test-unit test-integration test-system coverage coverage-fast clean upload \
        sync-skills playbook deploy-audit pool-warm pool-lease pool-status

PYPI_NAME := frob
SRC       := src
TESTS     := tests

# ---------- default ----------

# Runs each tool exactly once: format, lint, typecheck, test.
# T-0340: `core` prerequisite (see `check` above) so a prior `uv sync` that
# clobbered the editable natives is repaired before pytest collects.
all: core
	uv run ruff check $(SRC)/ $(TESTS)/ --fix --select I
	uv run ruff format $(SRC)/ $(TESTS)/
	uv run ty check $(SRC)/
	uv run pytest $(TESTS)/ -q -n auto

# Read-only gate (no auto-fix). Safe to run in CI.
# T-0248: fail loudly, before frob check even runs, if strata-core/frob-core
# source outpaces the built native extension -- otherwise frob check/frob
# test silently run against the stale native and give wrong results (the
# T-0166 review incident).
# T-0340: depends on `core` (not bare $(STAMP)) so `uv sync` clobbering the
# editable natives (see the `$(STAMP)` rule's own T-0340 note below) is
# self-healing on every invocation, not just `make coverage`'s. `core` is
# in .PHONY, so it always re-runs its recipe when listed as a prerequisite
# -- but `maturin develop` is a no-op rebuild in ~0.5s when nothing changed
# (measured: 14.6s cold from a fresh worktree with no cargo cache, 0.6s
# once cargo's target dir is warm), so this is cheap insurance, not a
# repeated full compile.
check: core
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
#
# T-0538: `$(STAMP)`'s `uv sync` (re-run whenever pyproject.toml is newer
# than the stamp) silently REMOVES the editable `strata_core`/`frob_core`
# natives `make core` installed -- `uv sync` reconciles the venv against
# only the declared dependency set, and the maturin-built natives are not
# in it. The incident: `make coverage` ran, `uv sync` clobbered both
# natives mid-run, and pytest then hard-failed collecting
# tests/system/test_frob_self_model.py with 44 phantom `frob check`
# violations (SYS004, 16 COV003, DRIFT fallout) until `make core` was
# re-run by hand. `frob doctor` (src/frob/doctor.py) already knows how to
# check + name this exact failure in one line, so it runs FIRST, right
# after the stamp-guarded sync -- a missing native now fails loudly and
# immediately (`frob doctor`'s own exit 1), before a single test collects,
# instead of surfacing as an oblique mid-suite ModuleNotFoundError. `make
# core` then unconditionally re-installs both natives (a from-source
# rebuild is a cheap no-op only in wall-clock terms if unchanged -- maturin
# still re-links -- but it is what restores what `uv sync` just removed)
# before pytest runs at all.
coverage: $(STAMP)
	rm -f .coverage .coverage.*
	$(MAKE) core
	uv run frob doctor
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
#
# T-0538: this target also depends on `$(STAMP)` (`uv sync`), so it is
# subject to the exact same natives-clobber hazard as `make coverage`
# above whenever it takes the incremental (non-fallback) branch -- the
# `$(MAKE) coverage` fallback branch already inherits the guard from
# `coverage:` itself. `$(MAKE) core && uv run frob doctor || exit 1`
# restores the natives and fails the whole recipe on one clear `frob
# doctor` line before any pytest collection is attempted.
BASE ?= main
coverage-fast: $(STAMP)
	@if [ ! -f .coverage ]; then \
		echo "coverage-fast: no prior .coverage data to append onto -- running full make coverage"; \
		$(MAKE) coverage; \
	else \
		$(MAKE) core && uv run frob doctor || exit 1; \
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

# ---------- worktree warm pool (T-0738, part 2 of T-0732) ----------
# Pre-creates N git worktrees with natives already built and `main`
# already merged in (docs/guides/worktree-pool.md), so `pool-lease`
# hands out a ready worktree instead of paying the per-worktree
# cargo/maturin build cost on the dispatch critical path. T-0877: these
# targets are thin delegates to the `frob scaffold pool` CLI subcommand
# (src/frob/app/scaffold_runner.py) -- no inline python left here.
N ?= 4
pool-warm:
	uv run frob scaffold pool warm $(N)

pool-lease:
	uv run frob scaffold pool lease

pool-status:
	uv run frob scaffold pool status

# ---------- install (stamp-guarded) ----------

# The `smt` extra (z3-solver) is opt-in and ships no wheel for some
# platforms (e.g. aarch64), where it fails to build from source; R7 degrades
# honestly without it. Sync only the routinely-buildable extras so a missing
# z3 wheel never bricks the dev environment. Install SMT support explicitly
# with `uv pip install "frob[smt]"` on platforms where z3 is available.
#
# T-0340: `uv sync` reconciles the venv against ONLY this stamp rule's
# declared dependency set -- the maturin-develop editable installs of
# strata_core/frob_core are not in it (they are not uv.lock-tracked
# dependencies, they are path-built native extensions installed out of
# band by `make core`), so every `uv sync` here silently EVICTS both
# natives if they were already installed. This rule cannot rebuild them
# itself (it has no `cargo`/`maturin` step and must stay usable on
# machines with no Rust toolchain -- see `core`'s own comment below), so
# the fix lives one level up: every target that actually needs the
# natives (`check`, `all`, `test*`, `install`, `coverage*`) now depends on
# `core` rather than bare `$(STAMP)`, and `core` is `.PHONY` so it always
# re-runs its (cheap, ~0.5s once cargo's target dir is warm) install step
# right after this rule's `uv sync` -- natives are restored before any
# consumer target's recipe body runs, instead of surfacing later as an
# oblique `ModuleNotFoundError`/`NativeExtensionUnavailable` mid-collection.
$(STAMP): pyproject.toml
	uv sync --extra serve
	@touch $(STAMP)

install: $(STAMP) core

# ---------- native extension (frob-core, Rust/PyO3) ----------

# T-0864: `core`'s recipe (below, in the `makefile-core-shim` managed
# block) is now a one-line delegation to `uv run frob natives build`
# (src/frob/natives/_build.py). The shared, git-common-dir-keyed
# CARGO_TARGET_DIR mechanism T-0732 built here (so a fresh worktree reuses
# another worktree's already-compiled dependency crates instead of a
# from-scratch cargo build every time -- T-0175's Done report measured
# ~34s/worktree cold) moved INTO that subcommand instead of being
# hand-maintained per-Makefile; cargo's own target-dir file lock still
# makes concurrent builds from sibling worktrees safe, unchanged. No
# `CARGO_TARGET_DIR` variable is defined at this Makefile layer anymore --
# `frob natives build` computes it itself.
#
# T-0865 tracks resyncing the scaffold template
# (`src/frob/scaffold/_managed.py`'s `_MAKEFILE_CORE_SHIM`) that installs
# this same block into other repos to match the one-liner below; until
# that lands, this repo's own block is intentionally ahead of the
# template it was generated from -- not a regression.

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
# T-0177: `mcp` is `frob`'s own `[serve]` extra in pyproject.toml (mirroring
# `[smt]`) -- installing it via `--extra serve` here instead of a second,
# independently-pinned `--with "mcp>=..."` keeps the version constraint in
# exactly one place (pyproject.toml) rather than two that can drift apart.
install-tool:
	uv tool install --force --reinstall . --with ./strata-core --with ./frob-core --extra serve

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

# T-0340: all five test targets depend on `core` (not bare $(STAMP)) --
# see `check`'s T-0340 note above for why. Every one of these collects and
# runs pytest, which hard-fails with ModuleNotFoundError on strata_core/
# frob_core if a `uv sync` clobbered them since the last `make core`.
test: core
	uv run pytest $(TESTS)/ -q -n auto

test-fast: core
	uv run pytest $(TESTS)/ -q --testmon

test-unit: core
	uv run pytest $(TESTS)/unit/ -q -n auto

test-integration: core
	uv run pytest $(TESTS)/integration/ -q

test-system: core
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

# T-0789: bumping pyproject.toml's version without re-locking leaves
# uv.lock's own recorded frob version stale relative to pyproject.toml.
# `uv run` silently re-syncs that stale line on every subsequent
# invocation in every worktree cut from this commit, producing a
# working-tree uv.lock diff no agent hand-edited -- SCOPE001 then fires
# on that diff unless someone remembers to `git checkout -- uv.lock`
# first. Running `uv lock` here and committing the result closes the gap
# at the source: a worktree cut from this commit starts with uv.lock
# already in sync, so `uv run` has nothing left to silently rewrite.
upload: clean
	@set -a && . ./.env && set +a; \
	NEW=$$(uv run python scripts/bump_version.py); \
	uv lock; \
	git add pyproject.toml uv.lock; \
	git commit -m "chore: bump version to $$NEW"; \
	git push; \
	uv build && uv publish

# frob:managed-block BEGIN makefile-core-shim (frob scaffold apply -- do not hand-edit within markers)
# Build and install every declared [[native]] extension into the venv
# (T-0732/T-0864). Smart-dup R3+ and strata design-model parsing need
# them; everything else works without them. `frob natives build` (frob's
# own subcommand) reads frob.toml's [[native]] entries, is best-effort
# when the Rust toolchain is absent, and owns the git-common-dir-keyed
# shared CARGO_TARGET_DIR mechanism itself -- no cache logic lives in this
# Makefile anymore. Requires a STAMP variable (venv install stamp) to
# already be defined -- see the Makefile shim installed by `frob scaffold
# apply`.
core: $(STAMP)
	uv run frob natives build
# frob:managed-block END makefile-core-shim

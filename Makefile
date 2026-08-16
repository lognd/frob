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
# T-1426: `coverage combine` MUST be called with `--append`, always. The
# recipe's base `.coverage` file already holds real, correctly-merged data
# by the time this recipe reaches `combine` (pytest-cov's own xdist
# DistMaster.finish() combines every worker's data into it in-process,
# before pytest even exits). Root cause, confirmed by direct instrumentation
# of coverage.py 7.14.1: `coverage`'s CLI `combine` action only calls
# `self.coverage.load()` first when `--append` is passed
# (coverage/cmdline.py); without it, the FIRST write inside
# `CoverageData.update()` (invoked once per satellite file it unions in)
# calls `CoverageData._start_using()`, which unconditionally `erase()`s the
# base data file the very first time it is touched in that process
# (`if not self._have_used: self.erase()`) -- silently discarding
# everything pytest-cov already combined, before the satellite files are
# even unioned back in. Live-reproduced: src/frob/__main__.py measured at
# 136 real covered lines in `.coverage` pre-combine, 0 post-`combine`
# (no `--append`), 136 again post-`combine --append`. This is why T-1353's
# own regression test (`TestCombineRecoversDisjointSessions`) never caught
# it: that test exercises `coverage run --append` (a different code path)
# and never calls the `combine` CLI action at all.
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
# T-1180: three consecutive real runs of this target failed to produce a
# trustworthy coverage.xml -- a corrupted shim broke combine silently once,
# and four load-sensitive tests (three strata self-model + serve-watch
# tick; all pass in isolation, verified repeatedly) failed only under
# xdist+coverage parallelism and halted the recipe before combine/xml/stamp
# ever ran. Two changes fix this without weakening the actual pass/fail
# signal:
#   (1) a parallel-run failure no longer halts the recipe -- failed tests
#       are re-run ONCE, serially (no xdist, so a load-sensitive flake gets
#       a fair single-threaded shot), with coverage appended rather than
#       restarted; only tests still failing after that rerun fail the
#       target. combine/xml/stamp always run afterward regardless of
#       status, so a genuine flake can no longer block them.
#   (2) stale `.coverage.*` worker files from a PRIOR (separate) run are
#       always removed before this run's pytest even starts, so `coverage
#       combine` below only ever sees fresh files this exact invocation
#       produced -- the incident this fixes was a manual combine, run
#       without that upfront `rm`, silently skipping leftover files from
#       an earlier halted attempt ("2 of 7 data files" consumed). The
#       serial rerun below appends (`--cov-append`) onto the SAME
#       invocation's data rather than starting a second one, so there is
#       no window between the parallel pass and the serial rerun where a
#       second `rm` could race a still-warm worker file.
# `frob check --stamp-coverage` itself now refuses to stamp when the
# resulting coverage.xml looks deflated (TEST011's join-fraction heuristic,
# promoted from a WARN to a hard pre-stamp floor -- src/frob/gates/
# _coverage.py's `stamp_coverage`), so a bad xml can no longer produce a
# clean-looking stamp even if combine/xml themselves succeed.
# T-1235: subprocess children run with cwd inside tmp fixture repos, so
# COVERAGE_PROCESS_START must point at an rc whose `source`/`data_file`
# are ABSOLUTE -- pyproject's relative `source = ["src/frob"]` resolves
# against the child's cwd and measures nothing, stranding empty
# .coverage.* files in child cwds (loss A of the 2026-07-29 attribution
# diagnosis). The rc is generated fresh each run so $(CURDIR) is current.
# T-1335: two silent-failure defects found during T-1320. (1) this recipe
# used to exit with PYTEST's status only -- a `frob check --stamp-coverage`
# failure AFTER a green suite (e.g. "ERROR: stamp-coverage failed:
# WriteFailed") printed to stdout but still exited 0, so the stale/corrupt
# stamp this whole target exists to refresh could go unrefreshed with
# nobody the wiser. The stamp write's own exit status is now captured
# (`stamp_status`) and folded into the recipe's final `exit` -- a pytest
# failure still wins (existing behavior preserved) but a stamp failure
# after a green suite now fails the make, with an ERROR line naming it.
# (2) `coverage xml` used to die outright (no coverage.xml produced at
# all) on a combined-data entry pointing at a torn-down test-fixture path
# (observed: a subprocess-measured `src/demo/__init__.py` scaffold fixture
# that no longer existed by combine time) -- `coverage xml` needs to
# reopen each recorded source file to compute branch/line totals, and one
# missing file aborted the whole report. `-i`/`--ignore-errors` (the same
# flag the T-1320 manual recovery used, `coverage xml -i`) tells coverage
# to skip a file it cannot re-read and still produce a report for
# everything it can -- src/frob itself is never affected, only ephemeral
# non-source fixture paths that were never real coverage targets to begin
# with. (3) observational defect promoted to fixed: a repeatedly-crashing
# xdist worker ("node down: Not properly terminated" in the pytest-xdist
# log, confirmed reproducing live during this ticket's own verification
# run -- 5 separate workers went down in one invocation) drops that
# worker's ENTIRE coverage contribution, not just the specific test(s)
# reported as failed -- a crash bypasses the `sigterm = true` handler that
# would otherwise flush data on a clean termination. This is the same
# "always understates, never overstates" asymmetry independently reported
# against several real symbols during this ticket's investigation. The
# parallel run's own log is now captured and grepped for "node down"; if
# any worker crashed, the recipe escalates to a FULL serial rerun (not
# just `--last-failed`) so every test's coverage is recaptured rather than
# silently accepting a partial/deflated stamp. This is strictly more
# expensive than the old `--last-failed`-only path, but only pays that
# cost when a crash is actually detected.
# T-1353: root-caused the repeated "node down" crashes themselves (not
# just their recovery). `addopts` defaults to `-n auto` (one worker per
# core -- 12 on the investigation host); several tests in this suite
# (`test_repo_unrestricted_scan_is_clean`, `test_sys_gate_zero_violations`,
# `test_repo_design_and_declarations_are_self_conformant`, and similar
# self-model/self-conformance tests) themselves spawn subprocess/
# multiprocessing children to run frob's own gates against the repo, and
# EVERY one of those children is independently coverage-instrumented via
# `COVERAGE_PROCESS_START` (the T-0464 fix, needed to measure them at
# all). Running `-n auto` workers, each of which may itself fan out
# further coverage-traced subprocesses, oversubscribes this host's CPU
# and memory well beyond `-n auto`'s own one-worker-per-core assumption
# (confirmed live: 5+ workers went "node down" in a single invocation,
# consistently, on a 12-core/23GB host) -- coverage tracing's own memory
# and CPU overhead is exactly what `-n auto`'s sizing does not account
# for. `COVERAGE_WORKERS` caps the PARALLEL phase specifically (the
# serial recovery rerun already runs `-n 0`, unaffected) to a value with
# real headroom for that fan-out; override on a bigger/smaller host with
# `make coverage COVERAGE_WORKERS=N`. This does not by itself prove the
# post-recovery merge is correct (see `_coverage.py`'s `load_coverage`/
# `_symbol_branch` -- verified directly, and via a controlled two-phase
# disjoint-test `--cov-append` + `coverage combine` replay of this exact
# recipe shape, tests/unit/test_makefile_coverage.py) -- it addresses WHY
# workers crash in the first place, so the expensive full-serial-rerun
# fallback below is needed far less often.
# T-1353 (part 2 -- why the serial recovery rerun's OWN merged data was
# STILL wrong even after recovering from a crash): live-captured proof
# (.frob/last-coverage-rerun's stdout during this ticket's investigation)
# shows the serial (`-n 0`) recovery rerun above hitting `addopts`'
# `--timeout=120 --timeout-method=thread` on `test_sys_gate_zero_
# violations` (a whole-repo self-scan test, `check_self_conformance` in
# its call chain -- one of this ticket's own reported-deflated symbols).
# `--timeout-method=thread` does NOT forcibly kill the offending call on
# fire -- it dumps a traceback in a watchdog thread while the ORIGINAL
# call keeps running to completion in the background, un-killed. In the
# PARALLEL phase that zombie thread only ever corrupts its own doomed
# xdist worker (already handled: "node down" below). In THIS serial
# phase there is only one process for the ENTIRE REST OF THE SUITE, so
# that same zombie thread's later interference (observed: repeated
# `ValueError: I/O operation on closed file` from `logging`, 31,468
# occurrences in one captured run, starting at the timeout and continuing
# to the recipe's end) corrupts shared interpreter state for every test
# still to run in that one process -- exactly why symbols exercised
# near/after the stuck test (`check_self_conformance`,
# `check_process_bounds_obligations`) came out severely deflated (6.7%,
# 88.9% measured directly -- see tests/unit/test_makefile_coverage.py's
# `TestCombineRecoversDisjointSessions` for proof `coverage combine`
# itself is NOT at fault here) even on a rerun where nothing "crashed" in
# the node-down sense. `--timeout-method=signal` (SIGALRM, standard on
# Linux) actually interrupts the stuck call via an exception raised IN
# the main thread instead of a zombie watchdog -- passed on both `-n 0`
# reruns below, where there is no xdist process boundary to contain a
# thread-method timeout's fallout. `COVERAGE_WORKERS` (below) independently
# reduces how often either rerun path is needed at all, by making the
# initial parallel run's OWN OOM-driven crashes less likely in the first
# place.
# T-1433: the serial (`-n 0`) rerun phases above wedge on a dead-holder
# futex -- observed twice, one run hanging 12h52m before manual kill, with
# the pytest process single-threaded, no children, blocked in
# futex_wait_queue, and zero CPU seconds consumed over a 20s window. Root
# cause is still unconfirmed (leading suspects: a crashed xdist worker from
# the PARALLEL phase leaving a coverage/multiprocessing lock held that the
# serial rerun then blocks on forever; COVERAGE_PROCESS_START's subprocess
# coverage locks; or a leaked forkserver/semaphore from an earlier run --
# see tickets.md T-1433). `addopts`' `--timeout=120` (pyproject.toml) is a
# PER-TEST watchdog scoped to the test call itself -- it cannot catch a
# hang between tests, in fixture teardown, or in coverage's own save/lock
# machinery, which is exactly where this wedge was observed sitting.
# COVERAGE_RERUN_DEADLINE wraps each `-n 0` rerun in a coreutils `timeout`
# so a wedge fails loudly (nonzero exit, clear diagnostic) inside a bounded
# wall-clock budget instead of hanging indefinitely: `-k 30` sends SIGTERM
# first and escalates to SIGKILL after a 30s grace period for anything that
# ignores it (matches the "single-threaded, no children, blocked past a
# clean shutdown" shape observed both times). Override with
# `make coverage COVERAGE_RERUN_DEADLINE=<seconds>` for a slower machine or
# a deliberately larger serial suite.
# T-2240: the paragraphs above (T-1180/T-1235/T-1335/T-1353/T-1433) are
# kept as incident history for WHY the old inline recipe needed each
# piece of resilience it had -- `native_coverage_refresh`
# (src/frob/testing/_coverage_refresh.py) now owns the equivalent logic
# in Python (its own module docstring cites the same T-1677/T-1672/T-1676
# tickets), so `COVERAGE_RERUN_DEADLINE`/`COVERAGE_WORKERS`/
# `COVERAGE_XDIST_DEADLINE`/`COVERAGE_STACKDUMP_ENV` and the
# `.frob/coverage-subprocess.rc` file target that used to back them are
# retired along with the recipe body that read them -- see `coverage:`
# below and this ticket's Done report for the one disclosed parity gap
# (subprocess-coverage measurement) that removing the rc-file generation
# reopens, already accepted as a gap by `coverage-fast:`'s own T-1525
# migration.

# T-1469: `frob doctor` reports (never repairs) an IN_PROGRESS ticket with
# no live cross-worktree lease as unhealthy (`scan_stale_ticket_leases`,
# T-1131) -- a session that ends leaving exactly that shape (agent process
# killed/timed out mid-ticket) previously made every SUBSEQUENT `make
# coverage`/`make coverage-fast` abort at this precondition before pytest
# ever ran, costing a full run slot (third occurrence 2026-08-02). `frob
# ticket reconcile --apply` mechanically heals precisely this class
# (auto-requeues the stale hold, logs which ticket(s) it requeued) and is
# a NO-OP when there is nothing stale to fix -- running it unconditionally
# right before `frob doctor` means the doctor precondition can no longer
# abort on a stale lease specifically, while still failing hard on every
# OTHER doctor-checked condition (missing natives, corrupt derived state,
# a live land.lock, venv shim drift) that `reconcile` does not touch.
# T-2240: this recipe used to carry ~40 lines of its own crash-recovery/
# rerun/stamp shell logic (subprocess-rc generation, xdist-deadline
# timeout, node-down detection + full serial rerun, T-1363 never-promote-
# partial-on-failure, coverage combine/xml, final `frob check
# --stamp-coverage`). `frob.testing._coverage_refresh.native_coverage_
# refresh` (T-1516/T-1677/T-1672) reimplements all of that -- wall-clock
# + no-progress watchdog, xdist worker-crash signature detection with a
# one-shot serial `-p no:xdist` retry (the node-down path), T-1676's
# "keep the data, mark degraded" posture for an ordinary red suite, and
# a T-1363-equivalent guard (a watchdog-aborted run never reaches
# `coverage xml`/`stamp_coverage` at all: see `native_coverage_refresh`'s
# `_write_abort_provenance` branch) -- in pure Python, reachable via `uv
# run frob coverage --full` (T-1525's CLI entrypoint). `core` stays a
# real prerequisite (not a recipe-embedded `$(MAKE)` line -- T-2098's
# fix for the `make -n` compound-recursive-call hazard) so natives are
# never stale under a fresh checkout; `reconcile`/`doctor` stay as one
# `&&`-chained recipe line (no `$(MAKE)` on it, so `make -n coverage`
# still only PRINTS it) preserving the T-1469 stale-ticket-lease
# self-heal ahead of the run.
#
# Disclosed parity gap (pre-existing, not introduced here): neither this
# path nor `coverage-fast:` (already migrated under T-1525) generates
# `.frob/coverage-subprocess.rc`/sets `COVERAGE_PROCESS_START`, so a test
# that spawns `frob` (or anything else) as a real subprocess is not
# separately coverage-instrumented the way the old ~40-line recipe's
# manual rc + `coverage combine --append` measured it. `coverage-fast`
# already accepted this gap at T-1525; this leaf does not introduce a
# new one, but a follow-up to re-add subprocess-coverage measurement to
# `native_coverage_refresh` itself is real, tracked work (see this
# ticket's Done report).
coverage: core
	uv run frob ticket reconcile --apply && uv run frob doctor && uv run frob coverage --full

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
# `coverage:` itself. The recipe restores the natives (`uv run frob
# natives build`, same command `core:` itself runs) and verifies them
# (`frob doctor`) on their own lines, before any pytest collection is
# attempted.
# T-2098: this recipe used to read `$(MAKE) core && uv run frob ticket
# reconcile --apply && uv run frob doctor || exit 1` -- a SINGLE compound
# shell line. GNU make executes any recipe line containing the literal
# `$(MAKE)` even under `make -n` (a dry run), so the sub-make call itself
# is meant to recurse and trace; but because the line was a compound `&&`
# chain, `make -n coverage-fast` genuinely ran EVERYTHING on it, including
# `uv run frob ticket reconcile --apply` -- a MUTATING ledger write --
# against a real checkout, not just the intended sub-make trace. The fix
# is not a narrower `&&` split (that leaves the general trap: the next
# `$(MAKE)`-containing compound line reintroduces the same hazard); it is
# removing this target's dependence on a recursive `$(MAKE)` line
# entirely, per the standing direction to move workflows off recursive
# Makefile calls (T-1382). `TestMakefileNoCompoundRecursiveMake`
# (tests/test_coverage.py) statically guards that no recipe line in this
# file ever again combines `$(MAKE)` with another shell command via
# `&&`/`||`/`;`/`|`.
# T-1526: `coverage-fast` had no xdist-crash-recovery/rerun-deadline
# resilience of its own -- it was ~15 lines re-deriving exactly what
# `frob.testing._coverage_refresh.native_coverage_refresh` (T-1516) now
# does as a frob-native, cross-platform library call (decide cold-start-
# full vs. touched-set-incremental vs. nothing-to-do, spawn pytest/
# coverage directly, always finish with stamp_coverage). `frob coverage`
# (T-1525) is the CLI entrypoint over that same call, so this target is
# now a genuinely thin wrapper -- `coverage:` below is NOT rewritten the
# same way, since IT is the one that owns the crash-recovery/rerun-
# deadline shell logic this ticket's acceptance explicitly keeps
# Makefile-side (T-1516's own Done report already disclosed that
# resilience as deliberately not re-derived in Python).
BASE ?= main
coverage-fast: $(STAMP)
	uv run frob natives build
	uv run frob ticket reconcile --apply
	uv run frob doctor
	uv run frob coverage .

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
	uv run frob release stamp; \
	uv run frob release sync; \
	git add pyproject.toml uv.lock CHANGELOG.md .frob-release.json; \
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

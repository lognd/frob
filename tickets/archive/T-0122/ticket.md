---
id: T-0122
title: frob check races concurrent build_graph calls against shared .frob/cache.db
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/graph/**
- tests/unit/test_check.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestCollectResultsLogLevelRace::test_racing_tasks_restore_original_stdout_handler_level
- tests/unit/test_check.py::TestCollectResultsLogLevelRace::test_all_none_tasks_still_restore_level
- tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once
designated_repro_test: null
threat: null
component: null
---
Found while investigating T-0089 (test_scaffold_dx flake).

Root cause, reproduced deterministically outside pytest/xdist entirely: run
12 independent `frob scaffold python-tool` + full check pipelines (uv sync,
ruff, ty, pytest, frob check --stamp-coverage, frob check) concurrently as
plain OS processes (no xdist involved) on a 12-core machine. Under that CPU
contention, `frob check` intermittently exits 0 but its stdout+stderr never
contains the final summary line (no "N errors" text at all) -- i.e. the
process completes and returns success without ever emitting
`result.as_text()`'s output, which the caller (test_scaffold_dx.py) then
correctly flags as a failure.

Independently corroborated by the session coordinator: the same
missing-summary-with-exit-0 behavior was observed interactively in a
worktree during T-0074 verification, with duplicated "dispatching path=" /
"extracted N import specifiers" log lines.

Mechanism (partially confirmed, needs tracing to the exact swallowed
step): `_collect_results` in src/frob/check/__init__.py runs `_run_arch`
and `_run_gates` as separate tasks in the SAME ThreadPoolExecutor within
one `frob check` process. Both independently call into the graph-building
pipeline (frob.arch.analyze_project and frob.gates.run_gates each build
their own graph), and both open `frob.graph.cache.connect()` against the
SAME .frob/cache.db concurrently from separate threads. Captured logs show
every source file parsed and cache-written twice in parallel by the two
stages. cache.connect's WAL + busy_timeout=30s (T-0029) handles
cross-PROCESS contention, not this intra-process double-build.

Suspect fix directions:
- Build the graph ONCE per `frob check` invocation and pass the snapshot
  into both `_run_arch` and `_run_gates`.
- Or serialize all `cache.connect()` callers behind a single intra-process
  lock.

Do NOT fix by adding retries/timeouts/sleeps in callers (e.g.
test_scaffold_dx.py) -- that hides a real correctness bug (duplicate parse
work burning CPU, and a code path that can swallow the final report).
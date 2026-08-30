---
id: T-3478
title: build_graph holds the exclusive derived-state flock for the whole parse, serializing
  xdist workers into a ~19-minute CI tail stall
state: queued
kind: bug
origin: agent
created: '2026-08-30'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/__init__.py
- src/frob/process/_lock.py
- tests/unit/test_graph_build_lock.py
- tests/test_graph.py
- docs/modules/graph.md
- docs/commands/check.md
- docs/modules/process.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/graph.md
  reason: T-0918 docstring paragraph update required by acceptance criteria
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/commands/check.md
  reason: T-0918 docstring paragraph update required by acceptance criteria
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/process.md
  reason: derived_state_write_lock docstring cross-reference update required by acceptance
    criteria
  actor: logan
  at: '2026-08-30'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

`build_graph` (src/frob/graph/__init__.py:520) wraps its ENTIRE body --
repo walk (`_walk_repo_files` over ~8500 files), source parse
(`_ingest_source_files`), doc parse (`_ingest_doc_files`), stale-cache
prune, and finalize/commit -- inside a single
`with derived_state_write_lock(root):` block. That helper (T-0918,
src/frob/process/_lock.py:438) takes a real cross-process EXCLUSIVE
`fcntl.flock` (`derived_state_lock(root, exclusive=True)`,
src/frob/process/_lock.py:296) when called standalone (i.e. not nested
inside a same-process SHARED hold from `frob check`'s main thread).

Under `pytest -n <N>`, each xdist worker is its own process. Every
worker's `build_graph` call takes the SAME exclusive flock keyed on
`root` for the full walk+parse duration, not just the cache-mutating
tail (`_prune_stale_cache` + `_finalize_build`'s `commit`). Workers that
should run in parallel instead serialize behind each other for the
entire parse of ~8500 files, which is the measured ~19-minute CI tail
stall on ubuntu.

## Root cause

T-0918 chose to hold the exclusive lock around the whole rebuild for
simplicity/soundness, but the actual invariant it needs to protect is
narrower: no two processes may mutate the same `cache` sqlite file
concurrently. The walk and parse phases only build in-memory/local
state plus staged (uncommitted or per-row) writes to `conn`; they do
not need exclusivity against a concurrent reader, only against another
concurrent WRITER of the same cache. Holding the lock for the parse
(the expensive part) as well as the mutation (the cheap part) is why
this serializes workers instead of just serializing their cache
commits.

## Fix options

(a) [preferred] Narrow the exclusive hold: parse without holding
`derived_state_write_lock`, take it only around the actual cache
mutation (the `_prune_stale_cache` + `_finalize_build` sequence, i.e.
from opening the write transaction through `conn.commit()`). Walk and
parse happen unlocked and in parallel across workers; only the
short cache-write tail serializes. Must preserve T-0918's soundness
(no two processes committing to the same cache concurrently) and
T-1423's `CacheLocked` handling (still catch/report
`GraphError.CacheLocked` around whatever now sits inside the lock).

(b) [fallback, more invasive] Give each xdist worker its own cache
path (e.g. keyed by `PYTEST_XDIST_WORKER` or worker-scoped tmp cache)
so workers never contend on the same `cache` file/root pair at all.
Rejected as primary because it changes cache semantics/fixtures more
broadly and doesn't fix the underlying serialization for any other
concurrent-`build_graph` caller (e.g. two agents running `frob check`
in the same checkout), only the test suite's symptom.

## Must-fire / must-stay-quiet

- Two concurrent `build_graph(root, cache)` calls against DIFFERENT
  cache files (the xdist-worker-per-cache shape) must run genuinely
  concurrently after the fix (measure wall time: 2-concurrent should
  be close to 1x single-build time, not ~2x).
- Two concurrent `build_graph` calls against the SAME cache file must
  still serialize (or one must get `Err(GraphError.CacheLocked)`) --
  no torn/concurrent writes to one sqlite cache. This is T-0918's
  soundness invariant and must not regress.
- T-1423's `CacheLocked` behavior (retry budget exhausted ->
  `Err(GraphError.CacheLocked)`, never an unhandled exception) must
  still fire when the narrowed lock is contended.
- `frob check`'s existing SHARED/EXCLUSIVE reentrancy contract in
  `derived_state_write_lock`'s docstring (same-process nested call
  no-ops; standalone call takes a real exclusive lock) must be
  preserved for whatever now sits inside the lock.

Affected/relevant tests (bind via frob:tests as touched):
- tests/unit/test_graph_build_lock.py (new/expanded -- lock scope)
- tests/test_graph.py::TestLoadGraph::test_non_utf8_doc_file_is_skipped_not_crashed
- tests/unit/test_memo.py::test_build_graph_second_call_is_memo_hit
- tests/test_graph.py::TestBuildIncremental::test_stats_sum_source_and_doc_counts_not_difference
- any existing CacheLocked-path test in tests/test_graph.py (grep for
  `CacheLocked` in that file)
- any existing derived_state_write_lock reentrancy test under
  tests/unit/ (grep for `derived_state_write_lock`)

## Acceptance

- Update the T-0918 docstring paragraph on `build_graph` (and its
  cross-reference in `derived_state_write_lock`'s own docstring, plus
  docs/modules/graph.md and docs/commands/check.md's referenced
  sections) to describe the narrowed lock scope and why it is still
  sound.
- 2-process wall-time experiment (before/after) recorded in the Done
  report.
- The 6 tests above pass under
  `FROB_SUGGEST_ACK=1 uv run pytest -n 4 <ids>` with no "node down"
  line, on a quiet box.
- `uv run frob test` (touched set) clean, or a reasoned waiver.

---
id: T-3722
title: frob test --all prints stale/wrong xdist addopts warning
state: done
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_worktree_guard.py
- tests/test_worktree_guard.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/process/**
  reason: the xdist-addopts assumption lives in tickets/_worktree_guard.py, not process/**
  actor: logan
  at: '2026-09-03'
- op: add
  glob: src/frob/tickets/_worktree_guard.py
  reason: the xdist-addopts assumption lives in tickets/_worktree_guard.py, not process/**
  actor: logan
  at: '2026-09-03'
- op: add
  glob: tests/test_worktree_guard.py
  reason: evidence test file + affects()-closure doc for the touched xdist warning
    functions
  actor: logan
  at: '2026-09-03'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: evidence test file + affects()-closure doc for the touched xdist warning
    functions
  actor: logan
  at: '2026-09-03'
evidence:
- tests/test_worktree_guard.py::TestAddoptsSetsXdist::test_true_when_dash_n_present
- tests/test_worktree_guard.py::TestAddoptsSetsXdist::test_false_when_addopts_has_no_xdist_token
- tests/test_worktree_guard.py::TestAddoptsSetsXdist::test_false_when_pyproject_unreadable
- tests/test_worktree_guard.py::TestWarnIfXdistPluginMissing::test_must_stay_quiet_when_addopts_has_no_xdist_token
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
apollo FROBLEMS.md 2026-09-03: 'frob test --all' printed an ERROR claiming 'pytest addopts sets -n auto' on a repo whose addopts is just '-q', then reported PASS anyway. The message appears to fire from a stale template string or the wrong config source rather than the actual repo config.

## Failure log
- 2026-09-03 attempt 1: Declared scope src/frob/process/** does not contain the defect: the stale xdist-addopts warning is emitted by warn_if_xdist_plugin_missing/warn_if_xdist_bound_missing in src/frob/tickets/_worktree_guard.py, which hardcodes the assumption that this repo's own addopts sets -n auto (see its docstring: 'frob's own -n auto addopt is unconditional') instead of reading the target repo's actual pyproject.toml addopts (cf. src/frob/testing/_coverage_refresh.py's _neutralized_addopts, which already does this correctly). Callers are in src/frob/app/** and src/frob/testing/**. Nothing under src/frob/process/** is involved. Needs a ticket scoped to src/frob/tickets/_worktree_guard.py instead.
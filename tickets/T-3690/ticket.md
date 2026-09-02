---
id: T-3690
title: 'clear ubuntu self-gate floor: PERF003/PERF004 + ruff-format drift'
state: in-progress
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_scan.py
- src/frob/refactor/_scan_carry.py
- src/frob/app/telemetry/_state.py
- src/frob/graph/__init__.py
- tests/test_refactor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_refactor.py
  reason: T-3690's own perf-regression tests belong to _scan.py/_scan_carry.py's existing
    test file (fallback mission scope explicitly allows 'and their test files')
  actor: logan
  at: '2026-09-02'
body_changes:
- mode: set
  reason: add description and plan for clearing ubuntu self-gate floor items
  actor: logan
  at: '2026-09-02'
  old_length: 0
  new_length: 1353
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Four ubuntu self-gate floor items block `frob check` from reaching zero
errors on the ubuntu leg (test suite already green):

1. gate:PERF PERF003 at src/frob/refactor/_scan.py:259 -- nested loops
   with an equality comparison.
2. gate:PERF PERF004 at src/frob/refactor/_scan_carry.py:409 --
   sorted()/.sort() call in a loop.
3. ruff-format drift: src/frob/app/telemetry/_state.py and
   src/frob/graph/__init__.py (created/modified by the T-3411 leaf-module
   land, never ruff-formatted).

Both PERF findings were introduced by the T-3642 refactor-verb split.

## Plan

- PERF003 (_scan.py:259): identify the nested equality-comparison loop;
  apply the suggested fix (build a set/dict from the inner loop's
  collection once, then O(1) membership) if it is a real cross join.
  If genuinely per-iteration and not hoistable, waive with a reasoned
  frob:waive PERF003.
- PERF004 (_scan_carry.py:409): identify the sorted()/.sort() call
  inside a loop; hoist it out, or sort once if loop-invariant. Waive
  with a reasoned frob:waive PERF004 if genuinely required per
  iteration.
- ruff-format drift: run `uv run ruff format` on both files, verify
  `ruff format --check` clean. Behavior-only whitespace change.
- Preserve behavior exactly for the PERF fixes; add PERF-regression
  tests asserting the call-shape (not wall-clock).

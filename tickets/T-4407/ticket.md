---
id: T-4407
title: 'verify_runner.py exceeds LARGE001 800-line threshold: extract coverage-lock
  auto-commit helpers'
state: queued
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/verify_runner.py
- src/frob/app/_verify_coverage_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LARGE001: src/frob/app/verify_runner.py is 874 lines, over the 800-line
threshold, and will red the next ubuntu self-gate.

Extract the coverage-lock auto-commit helpers T-4041 added
(_COVERAGE_LOCK_REL, _auto_commit_coverage_lock) into a cohesive new
private module, e.g. src/frob/app/_verify_coverage_lock.py, and have
verify_runner.py import and call it. No behavior change; existing tests
must still pass unmodified (only their frob:tests binding target moves
if the symbol's qualified path changes). Re-measure line count after the
split to confirm it clears 800 with margin.

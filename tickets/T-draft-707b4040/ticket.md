---
id: T-draft-707b4040
title: test_narrowed_live_lease_wins_over_stale_declared_scope fails on current dev
  (CI run 35510697497 burn-down)
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine.py
- tests/gates_suite/test_fix_engine.py
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
Found while burning down CI run 35510697497 (dev @ e99570be, now an ancestor of dev tip 4483b1da29). Re-verified failing on current dev tip (not stale): tests/gates_suite/test_fix_engine.py::TestFixEngineScopeLease::test_narrowed_live_lease_wins_over_stale_declared_scope fails both in the original CI run (ubuntu+windows) and locally on dev tip. Needs investigation of the fix-engine's scope/lease precedence logic: a narrowed live lease should win over a stale declared scope, and currently does not (or the test's fixture/expectation itself is stale -- confirm which before changing behavior).
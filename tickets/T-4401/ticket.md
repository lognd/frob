---
id: T-4401
title: 'test_a_land_in_a_different_repo_is_not_counted fails on Windows: /proc and
  ps assumption'
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
- src/frob/app/coordinator_suite/*.py
- tests/unit/coordinator_suite/test_fleet_land.py
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: scripts/fleet_status.py
  reason: actual /proc-and-ps process enumeration lives here, per scope-closure warning
  actor: logan
  at: '2026-09-10'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34546329688, Windows leg only (ubuntu/macOS pass).

Node id: tests/unit/coordinator_suite/test_fleet_land.py::TestLandProcessRows::test_a_land_in_a_different_repo_is_not_counted

Assertion (verbatim):
    assert [r["pid"] for r in rows] == [100]
E   assert [] == [100]

Landed today by T-4377 per coordinator brief; Windows regression from that
land. The land-process-row lookup uses /proc and ps, both POSIX-only
mechanisms, so on win32 it silently finds zero rows instead of the fixture
PID. Fix: branch production code on sys.platform (declared reason) to use
a Windows-appropriate process enumeration for this lookup, or mark the
underlying scan function not-implemented-on-windows and skip the test with
the repo POSIX-only skip convention (see tests/unit/test_stackdump.py) if
the mechanism is POSIX-only by design.
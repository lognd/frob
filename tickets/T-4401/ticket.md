---
id: T-4401
title: 'test_a_land_in_a_different_repo_is_not_counted fails on Windows: /proc and
  ps assumption'
state: done
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
- docs/guides/coordinator-scripts.md
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
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: AFFECT001 requires updating the affects()-closure doc for land_process_rows
    alongside the T-4401 fix
  actor: logan
  at: '2026-09-10'
evidence:
- tests/unit/coordinator_suite/test_fleet_land.py::TestLandProcessRows::test_a_land_in_a_different_repo_is_not_counted
designated_repro_test: tests/unit/coordinator_suite/test_fleet_land.py::TestLandProcessRows::test_a_land_in_a_different_repo_is_not_counted
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
frob:waive BUG002 reason="the defect is win32-only and the test that
covers it (this ticket's designated repro) is skipped on win32 by the
fix itself, so it necessarily PASSES (via skip) at any commit when run
on Linux CI/dev machines -- there is no Linux-runnable form of this test
that fails before the fix and passes after. Verified out-of-band via
winrun (T-4401 agent session, Windows mirror): the pre-fix test content
fails with the exact CI assertion (assert [] == [100]) on real win32,
and the post-fix content skips cleanly there -- see the ticket's Done
report for the exact commands run."
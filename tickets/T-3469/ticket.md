---
id: T-3469
title: 'Lease-pin refusal regressed again: 11 gate errors now precede/replace the
  frob ticket start remediation in a bare worktree'
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
- src/frob/app/check_runner.py
- src/frob/check/__init__.py
- tests/system/test_cli_check.py
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
MEASURED on GitHub Actions run 33298117154 (ubuntu-latest, HEAD f821615ca, 2026-08-30), the first run where ubuntu completes the suite (17.7 min, 8 failures of 12777). Reproduce locally by node id with -p no:xdist first; a test that passes locally but fails on CI has an environment dependency and must be made hermetic, never skipped.

FAILING: tests/system/test_cli_check.py::TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
    assert "frob ticket start" in <output>; output is "frob check <wt>  [FAIL]  11 errors  4 warnings ..." with no lease-pin remediation text.
T-3028 fixed this test on 2026-08-29 (project-type misdetection let CHECK001 fire before the lease-pin refusal). It now fails again with ELEVEN errors preceding the refusal, so a newer gate (candidates: LANDPARITY001/002 from T-3456, or the T-3287 admission registry, or T-3296/T-3298 SCOPE changes) now runs BEFORE gate:PREWORK in a bare worktree and floods the summary. Find which rules produce the 11 errors (run the test locally, print the summary), and restore the invariant that the lease-pin refusal is the FIRST and only thing printed when a ticket lease is recorded elsewhere -- prework must short-circuit the run, not just add a line. Add the ordering as an explicit test.

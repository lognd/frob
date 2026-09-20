---
id: T-4563
title: 'T-4495 regression: the post-land sweep''s testsuite-glob ratchet auto-accept
  rewrites capability-via-ratchet.lock.json in the SHARED ROOT, DirtyMain-blocking
  every subsequent land'
state: done
kind: bug
origin: agent
created: '2026-09-17'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_effects.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_sweep_context_does_not_write_lock
- tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_testsuite_glob_growth_auto_accepts_and_writes_lock
designated_repro_test: tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_sweep_context_does_not_write_lock
acceptance:
- text: GIVEN a post-land sweep that observes testsuite glob growth WHEN it runs in
    the root checkout THEN it never writes the lock file into the root working tree;
    the growth is recorded by the NEXT land (which owns the lock write) or logged
    as a pending acceptance
  evidence:
  - tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_sweep_context_does_not_write_lock
- text: GIVEN a land WHEN it runs the same growth acceptance THEN it writes the lock
    inside its own composed commit exactly as the version bump is land-owned
  evidence:
  - tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_testsuite_glob_growth_auto_accepts_and_writes_lock
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-17 07:35 right after T-4495 landed (e4a459f9d): the root checkout showed docs/design/registry/capability-via-ratchet.lock.json modified (the new 'testsuite glob growth' auto-accept), and the next land (T-4524) was refused with DirtyMain naming that file as owned by other tickets. The lock is land-owned like the version bump (T-0731); any writer outside the land must be refused or redirected. Coordinator reverted the root file by hand to unblock the chain.
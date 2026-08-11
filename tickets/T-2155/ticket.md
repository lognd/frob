---
id: T-2155
title: 'land.lock is never reclaimed when its holder dies: a dead pid deadlocked 4
  concurrent lands for 25 minutes and presented as extreme contention'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_lock_liveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_lock_liveness.py
  reason: regression-lock test for land.lock SIGKILL self-heal via OS flock, mirroring
    TestSigkillMidStaging's fork-based pattern; new file, avoids the T-2114/T-2118
    lease on tests/test_ticket_land.py
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_lock_liveness.py::TestLandLockSurvivesSigkilledHolder::test_land_lock_reclaims_promptly_after_sigkill
- tests/unit/test_land_lock_liveness.py::TestRefuseIfLandInProgressSurvivesSigkilledHolder::test_refuse_if_land_in_progress_clears_promptly_after_sigkill
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---

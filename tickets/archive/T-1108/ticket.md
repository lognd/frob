---
id: T-1108
title: 'arch: extract remaining ~8 verb families from tickets/__init__.py (3489) and
  split tickets/_land.py (4762) -- T-1103 residue'
state: dropped
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- docs/modules/tickets.md
- tests/test_tickets.py
- tests/test_tickets_tiers.py
- tests/test_tickets_lease.py
- tests/test_tickets_lease_overlay.py
- tests/test_tickets_dispatch_stale.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_tiers.py
  reason: doable/leases/scope-breadth family split moved frob:tests-carrying functions
    across files owned by these test modules
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_lease.py
  reason: doable/leases/scope-breadth family split moved frob:tests-carrying functions
    across files owned by these test modules
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_lease_overlay.py
  reason: doable/leases/scope-breadth family split moved frob:tests-carrying functions
    across files owned by these test modules
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_dispatch_stale.py
  reason: doable/leases/scope-breadth family split moved frob:tests-carrying functions
    across files owned by these test modules
  actor: logan
  at: '2026-07-28'
- op: add
  glob: frob.lock
  reason: frob ack re-acknowledges tickets/__init__.py::_recover_missing_evidence_for_done
    digest shift caused by this split
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets.py::TestDoable::test_blocked_excluded
- tests/test_tickets_tiers.py::TestDoableLeafOnly::test_epic_and_story_never_surface
- tests/test_tickets_lease.py::TestDoable::test_ignore_lease_returns_raw_list
- tests/test_tickets_lease.py::TestShowBlocked::test_show_blocked_lists_reasons
- tests/test_tickets_lease.py::TestLeasedBy::test_precise_in_progress_does_not_hide_disjoint
- tests/test_tickets_lease.py::TestLeasedBy::test_real_source_scope_collision_is_hidden
- tests/test_tickets_lease.py::TestLeasedBy::test_over_broad_lease_demotes_to_warn_only
- tests/test_tickets_lease.py::TestLargeGlobWarnings::test_fires_on_broad_tests_glob
- tests/test_tickets_lease.py::TestLargeGlobWarnings::test_silent_on_precise_test_file
- tests/test_tickets_lease.py::TestBreadthPerf::test_computed_once_per_doable_call
- tests/test_tickets_lease.py::TestBreadthPerf::test_doable_blocked_also_shares_one_breadth_walk
- tests/test_tickets_lease.py::TestBreadthPerf::test_repo_files_git_kill_switch_refuses_without_spawning
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_live_lease_decorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_queued_with_stale_lease_undecorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_ledger_in_progress_undecorated
- tests/test_tickets_lease_overlay.py::TestDisplayState::test_no_root_never_decorates
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_no_lease_is_not_in_flight
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_no_root_never_in_flight
- tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_same_day_is_zero_hours
- tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_one_day_old_is_24_hours
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_under_threshold_no_alarm
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_medium_priority_never_alarms
designated_repro_test: null
acceptance:
- text: GIVEN the tickets package WHEN the remaining verb families (doable/leases/scope-breadth,
    scope mutation, field setters/sprint, evidence/transition, done-report/review/drop/attach)
    are extracted into per-family modules THEN tickets/__init__.py drops below 2000
    lines with no public API change and all existing tests pass
  evidence: []
- text: GIVEN tickets/_land.py at 4762 lines WHEN split into cohesive submodules (preflight,
    splice, verify, sweep families) THEN no single tickets/ module exceeds 2500 lines
    and LARGE001 no longer flags _land.py
  evidence: []
threat: null
component: null
---
T-1103 extracted archive + new/renumber families (tickets/__init__.py 4287->3489) and stopped on budget; per its done report the remaining ~8 families are doable/leases/scope-breadth, scope mutation, field setters/sprint, evidence/transition, done-report/review/drop/attach, and _land.py (4762 lines) was not touched. Continue the same extraction pattern: per-family private modules re-exported from __init__, zero behavior change, existing tests as the safety net. Beware the load-time circular import noted in T-1103's report (evidence family).

## Drop reason
- 2026-07-28: absorbed: T-1122 (done) landed the doable/leases/scope-breadth family this ticket's first slice; successor T-1123 carries the identical remaining scope (other verb families + _land.py split) with the accurate post-T-1122 line counts
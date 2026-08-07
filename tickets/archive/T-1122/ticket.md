---
id: T-1122
title: 'arch: extract doable/leases/scope-breadth family from tickets/__init__.py
  (T-1108 partial)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/tickets/_doable.py
- docs/modules/tickets.md
- tests/test_tickets.py
- tests/test_tickets_tiers.py
- tests/test_tickets_lease.py
- tests/test_tickets_lease_overlay.py
- tests/test_tickets_dispatch_stale.py
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
threat: null
component: null
---
T-1108 asked for the FULL remaining ~8-family extraction (tickets/__init__.py
below 2000 lines) plus a full _land.py split, with acceptance criteria
describing that entire migration. This dispatch only had budget for ONE
cohesive family, so acceptance could not be bound and T-1108 itself is
requeued rather than closed against unmet acceptance.

This ticket exists to close out and land exactly the family that WAS
completed this dispatch: doable/leases/scope-breadth extracted from
tickets/__init__.py into src/frob/tickets/_doable.py (T-1103's split
pattern, zero public-API change). See Done report for the full list of
moved symbols and the two monkeypatch/load-order hazards hit and fixed
along the way.
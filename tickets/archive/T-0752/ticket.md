---
id: T-0752
title: 'doable: priority column, in-flight/dispatchable split, and undispatched-critical
  staleness alarm'
state: done
kind: ux
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0716
parent: T-0715
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_no_lease_is_not_in_flight
- tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_no_root_never_in_flight
- tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_same_day_is_zero_hours
- tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours::test_one_day_old_is_24_hours
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_under_threshold_no_alarm
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_medium_priority_never_alarms
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_high_past_threshold_alarms
- tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_configured_threshold_from_frob_toml
- tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
designated_repro_test: null
acceptance:
- text: GIVEN a critical ticket unleased past threshold WHEN frob ticket doable runs
    THEN its row shows priority and an UNDISPATCHED alarm at the top of the dispatchable
    section AND frob check emits a TICK-family warning naming it
  evidence:
  - tests/test_tickets_dispatch_stale.py::TestUndispatchedStale::test_critical_past_threshold_alarms
  - tests/test_tickets_dispatch_stale.py::TestHasLiveLease::test_queued_with_live_lease_is_in_flight
  - tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
threat: null
component: null
---
User mandate 2026-07-22, after T-0731 (CRITICAL) sat filed-but-undispatched for hours while its conflict class kept firing: the doable listing must make dispatch state and priority impossible to miss. (1) PRIORITY COLUMN: doable renders the priority (critical/high/medium/low) per row -- ordering exists (T-0411) but is invisible today, so a critical at rank 4 reads like any other line. (2) DISPATCH-STATE SPLIT: rows with a live, non-stale lease (T-0716 overlay machinery) render in a separate IN-FLIGHT section (or an @worktree marker) below the truly-dispatchable rows, so line 1 of the top section is always the next thing to dispatch -- no mental subtraction of in-flight work. (3) STALENESS ALARM: a critical or high ticket that has been dispatchable (unleased, unblocked) longer than a configurable threshold (frob.toml, default 4h for critical / 24h for high, measured from the last state change or filing) gets a loud UNDISPATCHED marker on its row AND a TICK-family check warning, so the condition surfaces in frob check too, not only when someone happens to run doable. Coordinate with T-0714 (doable noise relocation) and T-0716 (lease overlay) -- one display surface, no duplicate lease-reading logic.
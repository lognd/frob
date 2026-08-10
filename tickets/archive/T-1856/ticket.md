---
id: T-1856
title: First-class anchor marker for permanent-waiver-target tickets
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- src/frob/tickets/_land.py
- tests/test_tickets_live_tracker.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_live_tracker.py
  reason: test coverage for T-1856's anchor marker + land-time terminal-land guard
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'COV002: sys sync-interface auto-updated this file''s tickets_ledger store
    interface to include the new set_anchor symbol; needs a frob:ticket edge'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/test_tickets_live_tracker.py::TestAnchorMarker::test_terminal_land_refused
- tests/test_tickets_live_tracker.py::TestAnchorMarker::test_non_terminal_land_not_refused
- tests/test_tickets_live_tracker.py::TestAnchorMarker::test_non_anchor_terminal_land_not_refused
- tests/test_tickets_live_tracker.py::TestAnchorMarker::test_set_anchor_requires_reason
- tests/test_tickets_live_tracker.py::TestAnchorMarker::test_set_anchor_round_trips
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1853 fixed the land-time refusal so a non-terminal land of a live-tracker-cited ticket is no longer blocked. Item 2 of T-1853's required list is still open: a first-class 'anchor' marker (explicit field or dedicated kind) so intent is declared rather than inferred from prose in the body -- today nothing stops a well-meaning agent from closing an anchor ticket in the name of draining the queue (T-1820 near-miss cited in T-1853's body). Design the marker, wire it into close/land guidance and doable output.
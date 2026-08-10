---
id: T-1822
title: Wire already_landed_markers into dispatch-time doable output/alarm
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
- src/frob/app/ticket_runner/_query.py
- tests/unit/test_app_runners_t1822_already_landed.py
- design/frob.strata
- src/frob/tickets/_doable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_app_runners_t1822_already_landed.py
  reason: 'T-1822: tests for the doable output/alarm wiring'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: 'T-1822: declare fs.write for the new test file (SELFAUDIT001)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/tickets/_doable.py
  reason: 'T-1822: remove the now-discharged WIRE001 waiver naming this ticket as
    follow-up'
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers::test_no_markers_prints_nothing_and_returns_empty
- tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers::test_flagged_ticket_prints_one_summary_line_and_is_returned
- tests/unit/test_app_runners_t1822_already_landed.py::TestDoableRowLandedMarker::test_flagged_id_gets_inline_marker
- tests/unit/test_app_runners_t1822_already_landed.py::TestDoableRowLandedMarker::test_unflagged_id_gets_no_marker
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
## Description
T-1744 case 1 added `frob.tickets._doable.already_landed_markers`
(read-only: which doable candidates already carry their own
`frob:ticket <id>` directive in a scoped file despite the ledger still
calling them queued/planned). It is intentionally NOT wired into any CLI
surface yet -- that wiring belongs in `frob.app.ticket_runner`, outside
T-1744's own declared scope.

## Plan
Wire `already_landed_markers` into `frob ticket doable`'s default render
(a WARN-severity decoration, same shape as `large_glob_warnings`) and/or
the dispatch-stale-alarm consumer, so a flagged ticket is visible to a
coordinator BEFORE it is dispatched, not just to a caller of the library
function directly.
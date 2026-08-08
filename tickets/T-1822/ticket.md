---
id: T-1822
title: Wire already_landed_markers into dispatch-time doable output/alarm
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
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

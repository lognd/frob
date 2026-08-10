---
id: T-2003
title: Add docs/modules/tickets.md anchor for is_effectively_in_progress (T-1999 follow-up)
state: done
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:grep -n "frob:describes src/frob/tickets/_leases.py::is_effectively_in_progress"
  docs/modules/tickets.md exit=0 sha256=33dfd91112af
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1999 added frob.tickets._leases.is_effectively_in_progress but could not add a frob:doc anchor in docs/modules/tickets.md because that file was leased by T-1696 (in-progress) at fix time. Add a short section documenting is_effectively_in_progress as the shared land-path liveness authority (lease-file-first, ledger-state fallback) and a frob:doc directive from the function back to it.
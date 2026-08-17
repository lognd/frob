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
land_commit: null
---
T-1999 added frob.tickets._leases.is_effectively_in_progress but could not add a frob:doc anchor in docs/modules/tickets.md because that file was leased by T-1696 (in-progress) at fix time. Add a short section documenting is_effectively_in_progress as the shared land-path liveness authority (lease-file-first, ledger-state fallback) and a frob:doc directive from the function back to it.

## Done report

Re-measured before writing: docs/modules/tickets.md had no anchor for
is_effectively_in_progress on current main (grep found none), so the
gap T-1999 left open was still real. Added a new section documenting
it as the shared land-path liveness authority (lease-first, ledger-
state fallback), with a frob:describes directive back to
src/frob/tickets/_leases.py::is_effectively_in_progress. Placed next
to the other lease-lifecycle sections (Orphaned-lease detection),
since this is read by the same class of land-path guard.

### Changed
```
 tickets/T-2003/ticket.md | 5 ++++-
 tickets/T-2024/ticket.md | 7 ++++++-
 tickets/T-2035/ticket.md | 7 +++++--
 tickets/T-2041/ticket.md | 5 ++++-
 4 files changed, 19 insertions(+), 5 deletions(-)
```

### Evidence
- `cmd:grep -n "frob:describes src/frob/tickets/_leases.py::is_effectively_in_progress" docs/modules/tickets.md exit=0 sha256=33dfd91112af` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, E501@/home/logan/projects/frob/.claude/worktrees/t2003-series/src/frob/app/ticket_runner/_rapid_sweep.py, PERF004@src/frob/tickets/_land.py, PII012@src/frob/testing/_coverage_refresh.py, PRE001@tickets/T-2003

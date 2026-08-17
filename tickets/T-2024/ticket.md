---
id: T-2024
title: Add the real frob:doc anchor for T-2006's revalidate_dispatchable_sweep_tickets
  once T-1696's tickets.md lease clears
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
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- cmd:grep -n "frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::revalidate_dispatchable_sweep_tickets"
  docs/modules/tickets.md exit=0 sha256=4773e06db8bc
- cmd:grep -n "frob:doc docs/modules/tickets.md#doable-time-revalidation-of-sweep-filed-tickets-t-2006"
  src/frob/app/ticket_runner/_rapid_sweep.py exit=0 sha256=0bfd28eda7a0
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2006 added `revalidate_dispatchable_sweep_tickets` (src/frob/app/
ticket_runner/_rapid_sweep.py) as a new public symbol with a COV001
waiver instead of a real frob:doc anchor, because its natural doc home
(docs/modules/tickets.md's existing deferred-post-land-sweep section,
T-1684/T-1983) is under T-1696's live cross-worktree lease.

Once that lease clears: add a short subsection to docs/modules/
tickets.md's deferred-post-land-sweep section describing
revalidate_dispatchable_sweep_tickets (called from frob ticket doable's
own render path, _query._doable) and its relationship to T-1983's
_close_resolved_sweep_tickets (same drop mechanism, different call-site
timing), then remove the COV001 waiver and add the real frob:doc anchor.

## Done report

Re-measured before writing: docs/modules/tickets.md had no doc entry
for revalidate_dispatchable_sweep_tickets on current main, so T-2006's
COV001 waiver was still live and the gap was real. Added a subsection
under the existing Deferred post-land sweep section describing the
function, its call site (_query._doable, before the dispatchable
filter), and its relationship to T-1983's _close_resolved_sweep_tickets
(same drop mechanism via _maybe_drop_resolved_ticket, different
call-site timing -- doable-time vs post-land-time). Removed the COV001
waiver on the function and replaced it with a real frob:doc directive
pointing at the new anchor.

### Changed
```
 tickets/T-2003/done-report.md | 27 +++++++++++++++++++++++++++
 tickets/T-2003/ticket.md      |  5 ++++-
 tickets/T-2024/ticket.md      |  7 ++++++-
 tickets/T-2035/ticket.md      |  7 +++++--
 tickets/T-2041/ticket.md      |  5 ++++-
 5 files changed, 46 insertions(+), 5 deletions(-)
```

### Evidence
- `cmd:grep -n "frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::revalidate_dispatchable_sweep_tickets" docs/modules/tickets.md exit=0 sha256=4773e06db8bc` (cmd evidence, exit=0)
- `cmd:grep -n "frob:doc docs/modules/tickets.md#doable-time-revalidation-of-sweep-filed-tickets-t-2006" src/frob/app/ticket_runner/_rapid_sweep.py exit=0 sha256=0bfd28eda7a0` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, DOC005@README.md, DOC005@docs/modules/cli.md, E501@/home/logan/projects/frob/.claude/worktrees/t2003-series/src/frob/app/ticket_runner/_rapid_sweep.py, PERF004@src/frob/tickets/_land.py, PII012@src/frob/testing/_coverage_refresh.py

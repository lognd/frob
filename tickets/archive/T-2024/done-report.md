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

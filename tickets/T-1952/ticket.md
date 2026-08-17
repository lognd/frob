---
id: T-1952
title: Re-ack docs/modules/tickets.md sections for T-1935's rapid-sweep wording change
  once T-1720's lease frees
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
- src/frob/app/ticket_runner/_rapid_sweep.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: the two waivers this ticket's own body says to drop live here, not in the
    doc file alone
  actor: logan
  at: '2026-08-11'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1935 changed _file_regression_ticket's and run_deferred_post_land_sweep's own count/wording (identity vs finding count caveat) in src/frob/app/ticket_runner/_rapid_sweep.py, but docs/modules/tickets.md#symbolic-attribution-t-1690 and #deferred-post-land-sweep-rapid-only-t-1684 could not be touched or re-acked because docs/modules/tickets.md was under T-1720's live lease at the time (frob:waive AFFECT001/DRIFT001 both reference this ticket). The underlying attribution/filing/sweep BEHAVIOR is unchanged -- only reported wording -- so no doc CONTENT edit is actually owed, but the ack/digest needs refreshing: run frob ack src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket and frob ack src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep once T-1720 releases the lease, then drop the two waivers.

## Done report

T-1720's lease had already freed (confirmed: no
.git/frob-leases/T-1720.json). Re-acked
src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket
and ::run_deferred_post_land_sweep, then dropped both waivers
(AFFECT001 on _file_regression_ticket, DRIFT001/AFFECT001 on
run_deferred_post_land_sweep) that cited the T-1720 lease block --
their reason no longer applies now that the ack succeeded. No doc
CONTENT edit was owed (T-1935 only changed reported wording, not the
attribution/filing/sweep behavior the doc describes), confirming the
ticket body's own premise.

Scope extended from docs/modules/tickets.md alone to also include
src/frob/app/ticket_runner/_rapid_sweep.py -- the two waivers this
ticket's own body says to drop live there, not in the doc file.

### Changed
```
 tickets/T-1899/done-report.md | 32 ++++++++++++++++++++++++++++++++
 tickets/T-1899/ticket.md      |  6 +++++-
 tickets/T-1952/ticket.md      | 14 +++++++++++++-
 tickets/T-1973/ticket.md      |  6 +++++-
 tickets/T-1996/ticket.md      |  6 +++++-
 5 files changed, 60 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-1899/src/frob/gates/_root_asset_dirs.py, PRE001@tickets/T-1952, TICK004@tickets.md

---
id: T-1758
title: T-1615's uniform ledger auto-commit does not cover programmatic (non-CLI) callers
  of new_ticket/write_ticket
state: done
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_store.py
- src/frob/app/ticket_runner/_new.py
- docs/modules/tickets.md
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
- tests/test_ticket_leases.py
- tickets/T-1758/ticket.md
- tickets/T-1758/done-report.md
- tickets/T-1799/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_new.py
  reason: new_ticket now auto-commits internally (T-1758's structural fix); the CLI
    verb must opt out via no_commit=True to preserve its documented single-commit-including-evidence
    behavior, otherwise --evidence would split into two commits
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/tickets.md
  reason: new_ticket's public-api signature/behavior doc entry needs updating for
    the new no_commit parameter and auto-commit behavior
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: new_ticket's own auto-commit makes _rapid_sweep.py's existing per-caller
    wrapper redundant/stale -- its new_ticket call must opt out via no_commit=True
    to preserve its documented nicer commit message, and the test encoding the old
    'new_ticket does not commit' premise needs updating to match
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: new_ticket's own auto-commit makes _rapid_sweep.py's existing per-caller
    wrapper redundant/stale -- its new_ticket call must opt out via no_commit=True
    to preserve its documented nicer commit message, and the test encoding the old
    'new_ticket does not commit' premise needs updating to match
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_ticket_leases.py
  reason: new tests for new_ticket's own auto-commit behavior; v2 per-ticket ledger
    files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1758/ticket.md
  reason: new tests for new_ticket's own auto-commit behavior; v2 per-ticket ledger
    files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1758/done-report.md
  reason: new tests for new_ticket's own auto-commit behavior; v2 per-ticket ledger
    files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1799/ticket.md
  reason: the misattribution follow-up draft filed as part of this ticket's own audit
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_programmatic_call_auto_commits
- tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_no_commit_leaves_ledger_dirty_and_warns
- tests/test_ticket_leases.py::TestNewTicketProgrammaticAutoCommit::test_new_verb_still_produces_one_commit_including_evidence
- tests/unit/test_rapid_sweep.py::TestCommitRegressionTicket::test_commits_the_ledger_write
designated_repro_test: null
threat: null
component: null
---
T-1755's investigation confirmed: `frob.tickets._new_renumber.new_ticket`
(and, by the same construction, `write_ticket`/other `frob.tickets`
mutators called directly rather than through the `frob ticket <verb>` CLI
dispatch) has NO auto-commit of its own. The T-1130/T-1615 auto-commit
(`commit_ticket_ledger_change`, `_auto_commit_ledger_after_dispatch`)
lives entirely in the CLI dispatch layer -- it wraps the verb, not the
library call the verb happens to invoke.

`frob.app.ticket_runner._rapid_sweep._file_regression_ticket` was one
concrete victim (fixed in T-1755): it calls `new_ticket` directly (a
detached child, not a CLI dispatch), so its write went uncommitted and
DirtyMain-blocked every subsequent land repo-wide.

This is a STRUCTURAL gap, not just that one call site: ANY current or
future programmatic caller of `frob.tickets.new_ticket`/`write_ticket`/
other ledger mutators that does not go through `frob.app.ticket_runner`'s
CLI dispatch table inherits the exact same silent-DirtyMain hazard.

Scope for whoever picks this up: audit `frob.tickets` for every
programmatic (non-CLI) caller of a ledger-mutating function
(`new_ticket`, `write_ticket`, `add_evidence`, etc. -- grep for direct
imports from `frob.app.ticket_runner`-external modules) and decide,
per T-1755's own two options:

1. Move the auto-commit INTO the library function itself (so it is
   impossible to call any ledger mutator without committing), or
2. Establish a documented convention that every non-CLI caller must
   call `commit_ticket_ledger_change` itself immediately after, and add
   a gate/lint that catches a caller which does not.

Option 1 closes the hole permanently; option 2 is weaker (relies on every
future caller remembering) but may be necessary if some programmatic
caller legitimately wants to batch several ledger writes into one commit
(same shape `commit_ticket_ledger_change(..., no_commit=True)` already
supports for the CLI layer).
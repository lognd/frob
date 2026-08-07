---
id: T-1758
title: T-1615's uniform ledger auto-commit does not cover programmatic (non-CLI) callers
  of new_ticket/write_ticket
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
---
id: T-3162
title: frob ticket reopen crashes mirroring to primary checkout (missing LEDGER_VERB_STRATEGY
  entry)
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_ledger_mirror.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
`frob ticket reopen` writes and commits its ledger change successfully
in a worktree, but then crashes with an unhandled exception:

```
ticket runner: 'reopen' has no LEDGER_VERB_STRATEGY entry in
frob.app.ticket_runner._ledger_mirror -- every verb in
_ticket_dispatch_table() must declare one (T-2603); add it before this
verb can auto-commit or mirror its ledger write
```

Measured directly while working T-3150 (series CG): `frob ticket reopen
T-3150 --reason "..."` reported `T-3150 reopened (done -> queued)` and
the worktree-local commit landed fine (`chore(tickets): reopen T-3150`),
but the mirror-to-primary-checkout step (the same T-2603 mechanism that
makes `kind`/`priority`/etc changes visible on main before the ticket
itself lands, seen working correctly for `frob ticket kind` earlier in
this same session) has no dispatch-table entry for `reopen` at all and
throws instead of mirroring. The reopen is real and committed in the
worktree, but invisible to the fleet (main's own ledger) until this
ticket eventually lands -- the same class of problem T-2603 exists to
prevent for every OTHER verb.

## Plan
Add a `LEDGER_VERB_STRATEGY` entry for `reopen` in
`frob.app.ticket_runner._ledger_mirror` (`_ticket_dispatch_table`),
matching the existing entries for `kind`/`priority`/`fail`/etc., so a
worktree-local reopen mirrors onto the primary checkout the same way
those do.

## Scope + leases
- src/frob/app/ticket_runner/_ledger_mirror.py

---
id: T-draft-21102fcc
title: frob ticket archive can strand a non-terminal ticket with no restore path (T-0450)
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_store.py
- src/frob/app/ticket_runner/*archive*
- src/frob/_cli_parsers/_ops.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/_cli_parsers/*
  reason: 'narrow: the restore/drop-archived CLI wiring belongs with the other ticket
    subcommands, not the whole parsers package'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/_cli_parsers/_ops.py
  reason: 'narrow: the restore/drop-archived CLI wiring belongs with the other ticket
    subcommands, not the whole parsers package'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2946 triage of TICK004 found T-0450 living under tickets/archive/T-0450/
(state: queued, priority: medium, created 2026-07-20 -- 37 days old) with no
body beyond its title. `frob ticket archive`'s own contract is "move
done/dropped tickets into tickets-archive.md" -- a queued ticket under
tickets/archive/ is therefore a ledger invariant violation: it was moved out
of the active queue without ever reaching a terminal state.

No CLI primitive exists to repair this safely: `frob ticket drop <id>` looks
up the active ledger only (confirmed: "NotFound: No ticket with that id"
against T-0450), and there is no `frob ticket restore`/`unarchive` command to
move a ticket's directory back into the active tickets/ tree. Hand-editing
the ticket directory or frontmatter directly is against this repo's own
standing rule (never hand-edit the ledger).

Two things worth fixing, either or both:
1. A `frob ticket restore <id>` (or `archive --undo`) primitive for exactly
   this repair case -- move a ticket's directory back into tickets/ and set
   state back to queued's prior value, git-tracked like every other ticket
   mutation.
2. `frob ticket archive`'s own write path should refuse (or at minimum warn
   loudly) if it is ever asked to move a non-terminal ticket -- whatever
   produced this state should not be able to reproduce it silently again.

T-0450 itself should be dropped once (1) exists (restore it to active first
so `drop` can find it, or extend `drop`/`evidence`-style commands to accept
an `--archived` flag the way `frob ticket evidence --archived` already does)
-- left queued-in-archive in the meantime, since neither this repo's tooling
nor its house rules give a safe way to correct it right now.

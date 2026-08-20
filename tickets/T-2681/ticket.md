---
id: T-2681
title: Add frob ticket unblock verb -- blocked_by can only be appended, never removed,
  via CLI
state: in-progress
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_ledger_mirror.py
- tests/test_ticket_lifecycle.py
- src/frob/_cli_parsers/_ticket/_closeout.py
- docs/modules/tickets-lifecycle.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout.py
  reason: unblock CLI parser lives alongside block parser in this file
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: 'AFFECT001: touch affects()-closure docs for LEDGER_VERB_STRATEGY and _unblock'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001: touch affects()-closure docs for LEDGER_VERB_STRATEGY and _unblock'
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket block <id> --by <blocker>` is the only writer of
`blocked_by` post-creation, and it can only APPEND -- there is no CLI
verb to remove a `blocked_by` entry. frob.tickets._doable._open_
blockers's own docstring documents this exact gap from a prior incident
(T-2076: a block against an in-progress ticket survived that ticket's
own later scope narrowing and "had to be cleared through the store API
by hand, because no unblock verb existed").

Hit again directly (T-1599, this session): a coordinator decision made
a blocked_by edge (T-1599 -> T-1598) genuinely obsolete -- T-1598 was
deliberately deferred and T-1599 rescoped to no longer depend on it --
and the only way to clear it was a one-off script calling frob.tickets.
_store.write_ticket directly (mirroring frob.app.ticket_runner.
_lifecycle._block's write path in reverse), then committing by hand via
_add_and_commit_tickets_md. That is correct in shape (goes through the
validated store API, not raw YAML text) but every caller has to
re-derive it from scratch, and it is easy to get wrong (skip the
commit, skip the land-in-progress check, edit the raw YAML instead).

Add `frob ticket unblock <id> --by <blocker>` (or `block --remove`),
mirroring `_block`'s own structure: validate `--by` is a well-formed
ticket ref, refuse loudly if it is NOT currently in `blocked_by` (the
membership-check mirror of `_block`'s duplicate-append refusal), then
write via the same `write_ticket` + `_add_and_commit_tickets_md`
pattern `_block` already uses.

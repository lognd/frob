---
id: T-draft-aa678380
title: 'TICK003 never clears in a busy repo: ticket archive refuses wholesale while
  any cross-worktree lease is live'
state: queued
kind: feature
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/app/ticket_runner/_archive.py
- src/frob/tickets/archive.py
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
Reported by the crunk session (2026-09-26): 143 done tickets sit
un-archived because `frob ticket archive` refuses while any worktree lease
is live (T-0843 guard), so TICK003 never clears in a repo that always has
an agent dispatched. Verified against dev b41443f46d: the only override is
`--force --reason`, which records an override for every run.

The guard protects tickets whose ledger dir a live worktree may still
touch. Deliver: archive only the done tickets that no live lease references
(by id or by scope on tickets/<id>/), skip the rest with one line naming
the blocking lease, exit 0 when at least one was archived; keep `--force
--reason` for the remainder. Positive control: two done tickets, one leased
in a worktree; plain archive moves exactly the unleased one.

---
id: T-4652
title: 'Ledger kernel: ids assigned once at new, draft promotion is a ledger-only
  land operation, one typed store API'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4651
tier: story
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic/story rollup for the kernel-decoupling epic:
  all file work lives in the leaf children; this ticket carries no write lease by
  design'
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LEDGER concern of the kernel-decoupling epic (T-4651).

Today the ticket ledger is reachable a dozen ways: src/frob/tickets/_store.py (2536 lines) is only one of them, and _new_renumber.py (1807) + _renumber_v2.py (441) + _draft_finalize.py (672) can each rewrite ids, including from inside a worktree. Measured consequence this week: draft ids renumbered inside worktrees, renumber races between concurrent agents, and 243 dangling draft-id citations on main after promotion (T-3929).

Target shape:
- an id is assigned ONCE, at `frob ticket new`. Nothing downstream renumbers.
- draft promotion is a LEDGER-ONLY operation, performed by land, that rewrites inbound citations as part of the same atomic write.
- one typed store API module (Result-returning, pydantic models in, pydantic models out) that every other frob module goes through -- no module opens tickets/<id>/ticket.md itself.

Frozen contract: the tickets/<id>/ticket.md on-disk format and the `frob ticket` CLI surface do not change.

---
id: T-5358
title: TICK015 requeues in-progress tickets that are merely waiting in the land queue
  (no live process), undoing lands and clobbering ledger states
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- tests/gates_suite/test_tick_dead_worktree.py
- frob.toml
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-5121's TICK015 fires from every frob check run and requeues any IN_PROGRESS ticket whose recorded worktree has no live process at that instant. In the queue-based fleet (ticket_land_default=queue) a finished ticket waits in .frob/land-queue.json with no process, so TICK015 requeued T-5293 (22:43, 'dead worktree') and others; their lands then refused (never-started) or landed code while the ledger stayed queued (T-5293, T-5267 on 2026-09-23 00:20 are done by content but queued by state). A gate must not mutate the ledger on a heuristic that every queued land satisfies. Fix: (1) never requeue a ticket that has a queued/landing entry in the land queue or a lease younger than a configurable age (default 6h); (2) make the requeue side effect opt-in ([gates] tick015_requeue = true; default report-only ERROR); (3) positive controls: a ticket with a live queue entry and a dead worktree is NOT requeued; a ticket with no queue entry and a 7h-old lease is. Coordinator repair after: close T-5293 and T-5267 whose code is on dev.
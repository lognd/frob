---
id: T-draft-adeca257
title: 'ledger: dead-pid land record lingers as ''write allowed during in-progress
  land''; rolled-back ticket new leaves an orphaned per-ticket lock and skips the
  id'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: T-5630
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
- src/frob/tickets/_land_queue.py
- src/frob/tickets/_lock.py
- src/frob/tickets/_new_renumber.py
- tests/unit/tickets/test_dead_land_record.py
- docs/modules/tickets-data-storage.md
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
Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-401: a land record from a dead pid (2461865, dated 2026-09-07) kept printing 'write allowed during in-progress land' on every ledger write for weeks until a real land reclaimed it. Separately, a `frob ticket new` that was rolled back by a concurrent land leaves an orphaned per-ticket lock (.frob/tickets/T-0423.lock) and the id T-0423 is skipped forever (the frob repo shows the same trace for T-5223/T-5346/T-5439). Deliver: (1) any ledger verb that finds a land record whose pid is dead retires it on the spot (guaranteed safe, logged) instead of warning; (2) a rolled-back `new` releases its per-ticket lock and returns the id to the sequence, or the next `new` reuses the lowest orphaned id; (3) `frob ticket reconcile` reports and (with --apply) clears orphaned per-ticket locks; positive control: fixture with a dead-pid land record and an orphaned lock -> both cleared by the next write, id reused.

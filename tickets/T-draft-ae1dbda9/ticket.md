---
id: T-draft-ae1dbda9
title: frob coord queue reorder|repair|requeue, and fix drain_next keying outcomes
  by ticket_id
state: queued
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: coord-surface
runs_last: false
milestone: v0.535.0
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob coord queue reorder <id> --front | repair | requeue: reorder moves a queued entry to the head under the queue lock; repair fixes bookkeeping (duplicate entries per ticket, entries stuck landing whose pid is dead or whose ticket is already done on dev, entries for done tickets) reporting each change; requeue re-enqueues the latest entry of a ticket that failed on a CAS race or a transient DirtyMain (not the ticket's fault) and leaves genuine refusals alone. Also fixes the engine bug measured 2026-09-24: drain_next records outcomes on the FIRST entry matching ticket_id, so a re-enqueued duplicate stays landing forever (T-5362, T-5326); the fix keys on the entry it marked, or enqueue refuses a duplicate. Red-first test reproducing that stall. Retires park.py, prune-queue.py, cas-requeue.sh and the coordinator's hand edits under the lock.

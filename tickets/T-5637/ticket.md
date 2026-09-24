---
id: T-5637
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
points: 8
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
- src/frob/coord/_queue_ops.py
- src/frob/tickets/_land_queue.py
- tests/unit/coord/test_queue_ops.py
- tests/unit/tickets/test_land_queue.py
- docs/modules/tickets-verify-sweep.md
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_coord.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/coord/_queue_ops.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/tickets/_land_queue.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/coord/test_queue_ops.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/tickets/test_land_queue.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: remove
  glob: src/frob/_cli_parsers/_coord.py
  reason: collides with in-progress T-draft-4ad886c1's live lease on this exact file;
    re-adding once COORD-1 lands and the lease clears (coordinator directive)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: drain_next/enqueue keying-fix and queue reorder/repair/requeue change documented
    behavior in the merge-queue reference docs
  actor: logan
  at: '2026-09-24'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: drain_next/enqueue keying-fix and queue reorder/repair/requeue change documented
    behavior in the merge-queue reference docs
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
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

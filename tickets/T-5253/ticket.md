---
id: T-5253
title: 'drain_next lands in blocked_by order: QueueEntry carries blocked_by, blocked
  entries wait, unsatisfiable blockers are rejected with a reason'
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
parent: T-5106
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_queue.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_land_queue*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: observed while draining with a shared-registry passenger (T-5138)
  actor: logan
  at: '2026-09-21'
  old_length: 858
  new_length: 1111
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Leaf B of T-5106 (~2 pts). Dependency-ordered drain.
- `QueueEntry` gains `blocked_by: tuple[str, ...]` captured from the ledger at enqueue time (extending the model keeps `_land_queue.py`'s seam discipline: `drain_next` never imports ledger internals).
- `drain_next` selects the OLDEST queued entry whose blocked_by ids are all done/dropped on the target branch (the caller passes a `resolved: Callable[[str], bool]`), skipping blocked entries without dequeuing them; an entry whose blocker is neither queued nor open is reported `QueueError.UnsatisfiableBlocker` and rejected back with the reason on its intent record.
- Second enqueue of a live id stays refused (AlreadyQueued); `--status` prints "waiting on T-xxxx" for a skipped entry.
- Positive control: three entries enqueued out of order land in dependency order; a cycle is rejected, not spun on.


Coordinator note 2026-09-21: enqueue drops per-call flags (--allow-cross-ticket, --push), and --drain applies its own flags to whichever entry is oldest. QueueEntry must carry the land flags the caller passed, and drain_next must apply them per entry.
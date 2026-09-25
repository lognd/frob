---
id: T-draft-f999a5f0
title: 'ledger verbs write before taking the lock: a lock-blocked verb dirties the
  root and refuses the land it waits on'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: high
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
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
- src/frob/tickets/_store.py
- src/frob/tickets/_lock.py
- src/frob/tickets/_land.py
- tests/unit/tickets/test_ledger_write_lock_order.py
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
Measured 2026-09-25 18:43-18:55 UTC: an agent's `frob ticket scope T-6523
--remove <glob> --reason ...` wrote tickets/T-6523/ticket.md to disk and
THEN blocked for 11+ minutes in flock (wchan locks_lock_inode_wait) on
the lock a running land held. Meanwhile the land (T-5814, 53 min in)
reached its pre-commit root-dirt check and was refused with

  root checkout has uncommitted changes belonging to ANOTHER open
  ticket's declared scope: tickets/T-6523/ticket.md

i.e. the verb's own write-before-lock ordering made the root dirty for
exactly as long as the lock it was waiting on was held, guaranteeing the
land it waited on would fail. The coordinator killed the verb and
committed its write by hand (1491a93714).

Deliver:
1. Ledger verbs (new/body/scope/block/set/evidence/done-report/drop/...)
   take the ledger lock BEFORE mutating any tracked file; while waiting
   they must leave the root byte-identical. If the wait exceeds its
   budget, refuse without having written.
2. The land's root-dirt check distinguishes "a frob ledger write in
   flight" (journal/lock holder is a live frob verb pid) from foreign
   dirt: for the former it waits up to the verb's own budget instead of
   refusing a 50-minute land, and logs the pid it waited on.
3. Positive control: a test that holds the land lock, runs `ticket
   scope --remove` in a subprocess with a 5 s wait, and asserts the
   ticket file is unchanged on disk until the lock is released; and a
   land whose root-dirt check sees a live-verb write and completes once
   the verb commits.

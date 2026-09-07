---
id: T-4271
title: T-3799's whole-file scope claim on frob.lock blocks concurrent frob ack from
  other tickets
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-3799/ticket.md
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
Found while landing T-4264: T-3799 (in-progress, PATHEXT/shutil.which fix) declared 'frob.lock' as one of its own scope globs -- a whole-file exclusive lease on the repo's shared doc-ack digest lock. Any OTHER ticket's 'frob ack' (a routine DRIFT001 remedy, unrelated to T-3799's actual PATHEXT work) writes to frob.lock and trips gate:CROSSTICKET (CROSSTICKET001) against T-3799, even though the two tickets' frob.lock edits are disjoint entries in an additive JSON structure. T-4264 worked around it with --allow-cross-ticket since its own frob.lock diff (2 ack entries, both unrelated to gitio/PATHEXT) is genuinely disjoint from T-3799's. Suggest: frob.lock probably should not be scope-able as a whole-file lease at all (like tickets.md's LEDGER_PATH treatment), or CROSSTICKET should special-case frob.lock the way it already does other append-only/merge-friendly ledgers, since a shared lock file lease starves every OTHER ticket's routine ack work for the lease-holder's whole lifetime.
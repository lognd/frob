---
id: T-5438
title: 'land: refuse at enqueue/dry-run when ticket state cannot transition to done'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
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
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
2026-09-23: T-5306 was refused at the real land on the CLOSE step with "illegal transition queued -> done" after the merge and squash had already run (~9 minutes of drain time), because the ticket was still `queued` (its worktree existed but `ticket start` never advanced it). T-5325 was in the same state at queue position 1 and would have failed identically. The land dry-run reported clean for both: it validates edges, leases and merge state but never checks that the ticket's ledger state can transition to done.

Fix: `frob ticket land` (enqueue path and --dry-run) must refuse up front when the ticket's state is not one the state machine can close from (in-progress), naming the verb that fixes it (`frob ticket work <id>` / `ticket start`). Cheap check, saves a whole drain slot per occurrence.

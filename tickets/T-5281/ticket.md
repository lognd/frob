---
id: T-5281
title: TICK015 appends a dead-worktree failure-log entry to a DONE ticket on the root
  ledger, uncommitted (DirtyMain for the next land)
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- tests/gates_suite/test_tick_dead_worktree.py
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
Observed 2026-09-22 05:30 on T-5261 (state done, landed as e1ee0f1704): tickets/T-5261/ticket.md on the root checkout gained an uncommitted '## Failure log' line '2026-09-22 attempt 1: TICK015: dead worktree (no live process holds worktree .claude/worktrees/t-5261), requeue' after a gate run. TICK015 (T-5121) must only consider IN_PROGRESS tickets and must never write to the root ledger from a gate run without committing; a landed ticket's worktree being idle is the normal state. Effect: the next queued land refused with DirtyMain until the coordinator discarded the file. Related: T-5256 (refusal residue on the root ledger).
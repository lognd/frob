---
id: T-draft-f01a9c4a
title: 'A refused land restores the worktree: ledger files, staged land-owned files
  and pre-land commits unwound, refusal text on the intent record'
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
blocked_by:
- T-4739
parent: T-5106
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_queue.py
- tests/ticket_land_suite/**
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
Leaf D of T-5106 (~2 pts). A refused land leaves the worktree exactly as it found it. Blocked by T-4739 (pure compose makes the unwind a no-op for tree state).
- Any refusal after finalize (sibling finalize failure, close failure, unscoped sweep refusal, timeout) restores the worktree's ticket ledger files (state back from done, draft ids back), unstages land-owned files, and removes the "wip: pre-land snapshot"/"finalize and close" commits it added, restoring the branch tip recorded at prepare.
- The intent record (`.frob/land-queue/<id>.json`) carries the refusal text verbatim and the branch tip it restored to; `--status` prints both.
- Replaces the coordinator's `git checkout -- tickets/ CHANGELOG.md` after every refusal. Positive control: a planted post-finalize refusal leaves `git status` clean and `state:` unchanged in the worktree.

---
id: T-5706
title: Record started_at and landed_at on tickets at their transitions (velocity substrate)
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Record started_at and landed_at on the ticket at the start and land transitions (derived once, stored; backfill from git land-commit dates for already-done tickets), so velocity, lead time and burndown are pure ledger reads instead of per-ticket git history walks. Positive control: a landed fixture ticket carries landed_at equal to its land commit date; a queued ticket has neither. Owner ask 2026-09-24 (velocity for sprints and milestones); see COORD-TREE.md section 6.

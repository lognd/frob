---
id: T-draft-88285df8
title: T-5105 blocked_by references T-draft-a693d397 which does not exist in the ledger
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-5105/ticket.md
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
found while land-prep dispatch on worktree t-draft-af37d815: T-5105's blocked_by lists T-draft-a693d397, which has no ticket.md anywhere under tickets/ or tickets/archive/ (never created or promoted) -- start refuses with BlockerOpen and cannot be cleared without either creating that ticket or removing the dangling blocker
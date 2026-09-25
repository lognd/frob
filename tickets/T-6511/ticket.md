---
id: T-6511
title: Document T-3047's review/decision node kinds in docs/strata/vmodel.md (blocked
  by T-3010 lease)
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: high
parent: T-3047
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
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- docs/strata/vmodel.md
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
found while working T-3047: KIND_REVIEW (requires commit+reason) and KIND_DECISION's new required reason attr are implemented and tested (strata-core/src/graph/vmodel/mod.rs) but docs/strata/vmodel.md was not updated -- held by T-3010's live scope lease throughout this ticket's work. Add a Node kinds entry for review, note decision now requires reason, once the lease frees.
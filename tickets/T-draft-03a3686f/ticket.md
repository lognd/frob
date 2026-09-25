---
id: T-draft-03a3686f
title: 'dropped: MongoDB schema-less drift (inconsistent field types/names across
  documents)'
state: dropped
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-929e1bd0
tier: ticket
sprint: store-family
runs_last: false
milestone: 0.538.0
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
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

Research file, Document anti-pattern #6. Static tier: "dynamic-only
(requires cross-file type-consistency inference across all writers of a
collection)" -- proving drift requires knowing every writer's actual
field types/names across the whole codebase and reconciling them
against real document shapes, which is a data-shape inference problem,
not a call-shape or repo-fact one.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule

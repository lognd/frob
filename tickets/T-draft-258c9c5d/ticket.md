---
id: T-draft-258c9c5d
title: 'strata kernel: semantic edge kinds refines/allocates/satisfies/verifies/decides/supersedes'
state: queued
kind: feature
origin: human
created: '2026-09-23'
priority: medium
parent: T-3004
tier: ticket
sprint: strata-vmodel
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-3004
  reason: epic section 3 leaf, owner-reviewed tree 2026-09-23
  actor: logan
  at: '2026-09-23'
- field: sprint
  old_value: null
  new_value: strata-vmodel
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Epic T-3004 section 3 (graph-not-blocks): the organizing relation between development artifacts is a set of typed semantic edges, not blocked_by. This leaf adds the edge kinds refines, allocates, satisfies, verifies, decides and supersedes to the strata-core graph kernel (model.rs, query.rs) and the .strata grammar, queryable by kind, with a required reason on supersedes and a named parse error for an undeclared kind. Positive control: a .strata file declaring `A satisfies B` and `D supersedes C reason "..."` parses into typed edges queryable by kind; an undeclared kind is rejected at parse time; a supersedes edge without a reason is rejected. Doc: docs/strata/graph.md gains a "Semantic edges" section. Owner-reviewed tree: scratchpad STRATA-VMODEL-TREE.md (2026-09-23). T-3047 (review and decision nodes) is blocked by this leaf.

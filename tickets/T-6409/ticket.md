---
id: T-6409
title: 'dropped: EAV (entity-attribute-value) schema detection from data shape'
state: dropped
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6463
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
body_changes:
- mode: append
  reason: 'DOC006: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 645
  new_length: 783
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
flavour: null
due: null
rank: null
---
Research file, Relational anti-pattern #2. Static tier: "dynamic-only
for detecting 'is this actually EAV' from schema shape; static (config)
once table/column names match the pattern" -- the table/column-name
heuristic alone is too weak to file as a real rule (any generic
`Attribute`/`EntityAttribute`-named model trips it, whether or not the
design is genuinely EAV), and the load-bearing signal (is this table
ACTUALLY being used generically, i.e. attribute-name cardinality/value-
type variance) is runtime data a linter cannot see from source.

Reason: dynamic-only -- becomes a frob:tests / EXPLAIN-style obligation,
never a static rule.


frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its scaffold, none exists on dev yet"

## Drop reason
- 2026-09-25: dynamic-only: becomes a frob:tests / EXPLAIN-style obligation, never a static rule

---
id: T-draft-151e03f4
title: 'Derive scope/points roll-up: parent scope is the union of children, parent
  points a read-only sum of leaves'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5749
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
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
- src/frob/tickets/_models.py
- src/frob/tickets/__init__.py
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
Derive scope/points roll-up: a parent's effective scope is the union of its children's glob sets; a parent's displayed points is a read-only sum of leaf points.

Positive control: a parent with two children scoped a/** and b/** reports a derived scope covering both and refuses a direct frob ticket scope write on a non-leaf tier.

Doc page: docs/modules/tickets-data-storage.md#points-t-5132

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

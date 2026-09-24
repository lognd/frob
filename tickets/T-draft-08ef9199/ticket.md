---
id: T-draft-08ef9199
title: 'TIER006: cross-relation guard -- relates/duplicates/supersedes edges never
  act as a second parent'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-draft-d17aa621
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
- src/frob/gates/_tickets_gate.py
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
TIER006: cross-relation guard -- relates/duplicates/supersedes edges are never used as a second parent; refuse or flag a strata semantic edge doing parent-shaped work. Lands at WARN.

Positive control: a ticket that two tickets both claim as parent via a semantic-edge workaround is flagged; normal single-parent tickets stay quiet.

Doc page: docs/modules/tickets-data-storage.md#data-models

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

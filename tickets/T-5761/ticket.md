---
id: T-5761
title: 'Census script: enumerate stories by flavour candidate, epics by all-children-done,
  childless stories, and the 11 kind: invariant tickets'
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
points: 2
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
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Census script (scratchpad only, no ledger writes): enumerate the 39 tier: story tickets by flavour candidate (user-facing vs non-functional), the 42 tier: epic tickets by all-children-done status, childless stories acting as oversized tickets, and the 11 kind: invariant tickets slated for reclassification.

Positive control: script output row counts match the 42/39/913 tier census and the 11 kind: invariant count exactly.

Doc page: none (working artifact)

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

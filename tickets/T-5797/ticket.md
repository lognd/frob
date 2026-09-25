---
id: T-5797
title: 'TIER002: resolve frob:verifies against the strata V-model graph'
state: queued
kind: feature
origin: agent
created: '2026-09-24'
priority: medium
blocked_by:
- T-5763
parent: T-5748
tier: ticket
sprint: null
runs_last: false
milestone: null
flavour: null
due: null
rank: null
points: 3
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
triage_changes:
- field: parent
  old_value: null
  new_value: T-5748
  reason: part of the ledger-tiers story (T-5748), TIER002 graph-validation follow-up
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: null
  new_value: '3'
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
found while working T-5763 (B2, ledger-tiers): TIER002's user_story branch currently only checks a frob:verifies <target> directive is PRESENT in the story body; it does not resolve <target> against the real strata V-model graph (verifies edges, customer-level artifact nodes) the way TIER002's quality_objective branch resolves frob:invariant against the real loaded invariant set. This graph-validated follow-up closes that gap.
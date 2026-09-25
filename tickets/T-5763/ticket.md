---
id: T-5763
title: 'TIER002: story closer -- all children done plus flavour-specific acceptance
  (user story V-model test node, quality objective bound invariant)'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5749
- T-5756
- T-5757
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
points: 8
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
- src/frob/gates/invariants.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '8'
  new_value: '8'
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
TIER002: story closer -- all children done PLUS flavour-specific acceptance: user_story requires a bound customer-level V-model test node; quality_objective requires a bound invariant at its declared (or derived) level. Per owner decision Q2 there is NO childless-story branch: a story with zero children is a finding (see D1's inverse), never a closable state. Lands at WARN.

Positive control: a user story with an open V-model verifies edge fails TIER002; a quality objective bound to a passing invariant at its declared level passes and stays quiet on re-run; a story with zero children is flagged, not closed.

Doc page: docs/strata/vmodel.md#the-five-closure-rules

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

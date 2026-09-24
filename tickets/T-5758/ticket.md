---
id: T-5758
title: 'TIER-DEPTH lint: three nested tickets under one story flags promote-to-epic;
  a childless story is also a finding'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5756
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
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
TIER-DEPTH lint: three (configurable) nested tickets under one story flags 'this story is an epic; promote it' as a WARN finding. Inverse (owner decision Q2): a story with zero children is also a finding.

Positive control: a story with 3+ levels of ticket nesting under it is flagged; a story with 2 levels stays quiet; a story with zero children is flagged.

Doc page: docs/modules/tickets-lifecycle.md

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

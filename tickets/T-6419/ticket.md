---
id: T-6419
title: 'invariant stories: split evidence into child tickets and retire TicketKind.invariant'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-5766
parent: T-5748
tier: ticket
sprint: null
runs_last: false
milestone: v0.536.0
flavour: null
due: null
rank: null
points: 5
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
- field: parent
  old_value: null
  new_value: T-5748
  reason: part of the ledger-tiers story (T-5748), the E2 scope cut
  actor: logan
  at: '2026-09-25'
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working E2 (T-5766, ledger-tiers): the 11 kind:invariant tickets (T-3962, T-3989, T-4039, T-4075, T-4078, T-4090, T-4092, T-4993, T-5203, T-5268, T-5386) were reclassified tier=story/flavour=quality_objective in T-5766, but per owner decision Q3 each still needs exactly one child ticket created to carry its evidence, and TicketKind.invariant needs retiring from the enum once that split is done. T-5203 and T-5268 are already state=dropped -- they need the tier/flavour reclassification only (already done in T-5766), no evidence-split child (nothing to carry).
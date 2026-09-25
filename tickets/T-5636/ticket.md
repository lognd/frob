---
id: T-5636
title: 'Close T-2982: parent the ci leaves under it, retag to v0.535.0, close when
  they land'
state: queued
kind: docs
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5805
- T-5633
- T-5638
parent: T-2982
tier: ticket
sprint: coord-surface
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
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
- field: parent
  old_value: null
  new_value: T-2982
  reason: T-2982's command surface (owner decision 2026-09-24)
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Close T-2982: parent the ci leaves under it, retag the epic to v0.535.0, confirm its three original children (T-2983, T-2984, T-2985) are done in the archive, and close the epic once the ci leaves land. Ledger via frob verbs only.

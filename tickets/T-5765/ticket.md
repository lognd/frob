---
id: T-5765
title: Enforce single-parent, no-epic-under-epic and milestone-is-top constraints
  at write time
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
- src/frob/tickets/_models.py
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
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '3'
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
Enforce single-parent, no-epic-under-epic and milestone-is-top constraints at write time (_validate_parent family).

Positive control: frob ticket new --tier epic --parent <other-epic> is refused; frob ticket new --tier milestone --parent <anything> is refused.

Doc page: docs/modules/tickets-data-storage.md#data-models

Owner decision Q2: every story has at least one child ticket; a one-change story is a story plus exactly one ticket created together via frob ticket new --tier story --with-ticket. Add the --with-ticket path here or in D2, whichever owns the runner surface; record the choice in the done report.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

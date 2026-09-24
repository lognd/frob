---
id: T-5775
title: 'Tiered auto-close: parent auto-transitions to DONE when the last child''s
  close satisfies TIER002/003/004'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-draft-9570bf46
- T-draft-ea1c92d6
- T-5774
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
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
scope:
- src/frob/tickets/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
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
Tiered auto-close: when TIER002/003/004 preconditions go from unmet to met on the last child's close, auto-transition the parent to DONE with a logged triage_changes entry -- no separate manual close for the guaranteed-safe path. Take care that landing one leaf does not silently land an epic with no evidence of its own beyond the roll-up.

Positive control: closing the last open child of a fully-ready epic auto-closes the epic in the same operation and records a triage_changes entry; closing a non-last child leaves the parent untouched.

Doc page: docs/modules/tickets-lifecycle.md

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

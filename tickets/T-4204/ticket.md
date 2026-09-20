---
id: T-4204
title: 'refusal messages: state the self-citation remedy first, and always name a
  copy-pastable remedy for cross-ticket-leakage refusals'
state: queued
kind: ux
origin: agent
created: '2026-09-07'
priority: low
parent: T-4135
tier: ticket
sprint: v0.537.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.537.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-355 (T-4135), both items: (1) cross-ticket-leakage refusal when two tickets share a worktree doesn't name its remedy (close the other ticket in this worktree, or move its files out) even though the rule itself is correct; (2) a waiver whose live-tracker citation is this same closing ticket has exactly one sensible remedy (re-point/drop the citation in this same diff), but the generic two-remedy message lists 'file a successor ticket' first, which produced a junk ticket filed only to satisfy the gate. Fix: detect the self-citation case and state its one remedy outright; for the general case, always state a remedy, not just the rule. Fixture-testable: YES.
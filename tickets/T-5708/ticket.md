---
id: T-5708
title: 'frob coord velocity [--sprint | --milestone]: points per day, forecast, lead
  time, slot efficiency'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: T-5630
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
- field: parent
  old_value: null
  new_value: T-5630
  reason: coord/agent/ci command-surface epic (owner decision 2026-09-24)
  actor: logan
  at: '2026-09-24'
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob coord velocity [--sprint L | --milestone M]: points landed per day over the window and the trailing seven days; remaining points; forecast finish date with a range from day-to-day variance; lead time from created to landed (median and p90); land-slot efficiency (lands attempted vs refused, from the land queue's recorded outcomes: a refusal costs the slot); cost per point in tokens once T-5279 fills the usage fields. --json prints the model. Positive control: a fixture sprint with three landed tickets (5, 3, 2 points over two days) and two open (8, 5) reports 5 points per day, 13 remaining, forecast plus 2.6 days; an empty sprint reports zero, never skipped. Blocked by coord status (the stem) and the started_at/landed_at model leaf. Owner ask 2026-09-24; see COORD-TREE.md section 6.

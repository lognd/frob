---
id: T-draft-6fda9b93
title: 'frob coord plan: P50/P85 forecast, capacity to the due date, the cut line,
  --commit'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob coord plan --milestone M | --sprint L: forecast completion as P50/P85 dates by simulating from the observed daily throughput distribution (from coord velocity), compute capacity to the due date, rank the open tickets and draw the cut line where cumulative points exceed capacity. Per the tiered safety rule: showing the line is automatic (also in coord status); moving tickets below the line to the next milestone/sprint is a recommendation with the exact command; --commit applies it with a reason recorded on each moved ticket. Milestone closure (MSCLOSE001) must fail while un-gapped tickets sit below the line, so a deadline cannot be met by pretending. Positive control: a fixture milestone with due in 2 days, velocity 5 pts/day and 25 open points reports capacity 10, a cut line after the top 10 points, and the forecast beyond due; with due far away no cut line and no finding. Owner decision 2026-09-24.

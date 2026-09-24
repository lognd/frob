---
id: T-5638
title: 'frob ci: every GhError mode surfaces as a named error at the CLI, no tracebacks'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
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
frob ci error handling end to end: every ghio failure mode (gh missing, not authenticated, no GitHub remote, rate limited, run or job not found, empty log for a failed job) surfaces at the CLI as its named GhError with the fix named, exit code non-zero, no bare exception; fixtures for each mode.

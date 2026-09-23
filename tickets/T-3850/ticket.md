---
id: T-3850
title: re-verify and simplify Makefile core-prerequisite self-heal now that natives
  are lock-tracked deps (T-3845)
state: queued
kind: docs
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 1.0.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- Makefile
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.532.0
  new_value: backlog
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: v0.532.0
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
- field: sprint
  old_value: backlog
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
T-3845 made frob-core/strata-core real default [project] dependencies (with a [tool.uv.sources] local-path override for this checkout). Verified 2026-09-05: a plain 'uv sync' in the T-3845 worktree no longer evicts the natives (they're part of the declared, lock-tracked dependency set now), which was the whole reason the Makefile's core-as-prerequisite self-heal machinery (T-0340) exists. Re-verify this holds across a fresh worktree / CI, and if so, simplify or remove the now-redundant prerequisite wiring in the Makefile. Filed as a follow-up per T-3845's Done report rather than done under that ticket (Makefile was out of its declared scope).
---
id: T-4190
title: 'lint: a *_path Field default that is a relative path should be flagged'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
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
- src/frob/gates
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.538.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.538.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-307/H3-5 (T-4109): no gate compares an AppConfig default filesystem path against a deployment manifest, because none exists on main -- but the cheap gate-worthy version needs no manifest: a Field(default=...) on a *_path-named field whose value is a relative path is itself a smell. Fixture-testable: YES, in frob's own pydantic AppConfig-shaped models.
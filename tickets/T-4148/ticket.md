---
id: T-4148
title: route frob.testing coverage pytest spawn and xdist check through project env
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_coverage_refresh.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/_coverage_refresh.py
  reason: 'T-4148: the bare pytest argv (F-017) and the xdist plugin-presence check
    (F-018) both need to route through the target project''s own uv-managed environment
    instead of frob''s'
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3887 F-017/F-018: frob coverage --full spawns a bare pytest from frob's own environment (F-017), and coverage refresh assumes pytest-xdist is installed in frob's environment, not necessarily the project's (F-018). frob.process._project_tool (T-3887/T-4125) routes ty/ruff spawns through uv run --project <root>; frob.testing._coverage_refresh's own pytest invocation(s) need the same treatment -- check first whether frob.process._pytest_spawn (referenced in docs/modules/process.md's pytest-spawn-resolution-t-3311 section) already covers this partially. Missing pytest-xdist in the PROJECT's env must be a loud typed error naming pytest-xdist and its install command, never a silent frob-env fallback or a silent loss of parallelism.
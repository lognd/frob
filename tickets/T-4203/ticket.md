---
id: T-4203
title: test.runner rootdir resolution must not depend on which path subset pytest
  was invoked with
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing
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
Consumer F-338 (T-4135). A nested pyproject.toml's [tool.pytest.ini_options] wins when pytest is invoked with only its own subtree, and the root's pythonpath (needed to import a sibling scripts/ dir) is silently dropped -- so a system test passes standalone and fails from the repo root, or vice versa. The configured test.runner invocation must resolve the same rootdir regardless of which paths it is given. Fixture-testable: YES.
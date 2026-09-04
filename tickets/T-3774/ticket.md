---
id: T-3774
title: 'ty win32 error: os.major/os.minor unnarrowed after T-3768 replaced the sys.platform
  assert with skipif'
state: queued
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_fleet_status_ground_truth.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_fleet_status_ground_truth.py
  reason: restore ty platform-narrowing for os.major/os.minor
  actor: logan
  at: '2026-09-04'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

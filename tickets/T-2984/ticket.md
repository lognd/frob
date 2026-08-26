---
id: T-2984
title: 'gh_io part 2: structured CI failure reporting -- typed run/job/step/test-node
  records, clustered by signature, no raw log grepping'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-2982
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/ci_report.py
- tests/test_ci_report.py
- docs/modules/ci_report.md
- tickets/T-2984/*
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/ci_report.py
  reason: structured CI failure reporting on top of ghio
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_ci_report.py
  reason: structured CI failure reporting on top of ghio
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/ci_report.md
  reason: structured CI failure reporting on top of ghio
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tickets/T-2984/*
  reason: structured CI failure reporting on top of ghio
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2982
  reason: 'T-2982 decomposition: seam, reporting, validity'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

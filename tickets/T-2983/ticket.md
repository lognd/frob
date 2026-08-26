---
id: T-2983
title: 'gh_io part 1: typed gh seam with named failure modes (no gh, no auth, no GitHub
  remote, rate limit, empty-log-on-failed-job)'
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
- src/frob/gh_io.py
- tests/test_gh_io.py
- docs/modules/gh_io.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gh_io.py
  reason: 'greenfield gh_io seam module: typed Result-returning gh subprocess seam
    per T-2982 part 1'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_gh_io.py
  reason: 'greenfield gh_io seam module: typed Result-returning gh subprocess seam
    per T-2982 part 1'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/gh_io.md
  reason: 'greenfield gh_io seam module: typed Result-returning gh subprocess seam
    per T-2982 part 1'
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

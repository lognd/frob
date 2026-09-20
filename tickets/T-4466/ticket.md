---
id: T-4466
title: 'REF002: docs/design/macos-portability.md has only one inbound reference'
state: queued
kind: bug
origin: human
created: '2026-09-13'
priority: medium
parent: null
tier: ticket
sprint: v0.544.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/macos-portability.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.544.0
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
MEASURED via frob check --ticket T-4463 (repo-wide REF002 gate, unrelated to T-4463's own scope): docs/design/macos-portability.md has exactly one inbound reference (docs/index.md) -- REF002 wants a second consumer/declaration or a frob:waive. Pre-existing since at least T-3488/T-3586; not something T-4463 touches. File a second consumer/anchor or waive with reason.
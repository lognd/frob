---
id: T-4231
title: extend the PII-structural gate to model the message/extra split inside a log
  record
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4175
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_pii_structural
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
Consumer F-373/P9 (T-4175): a redaction test passes secrets in the log message, which is the surface the filter handles; the PII gate is structural (it knows which nodes/files carry which PII classes) and does not model the message/extra split inside a log record, so a secret passed via extra= would be invisible to both the filter and the gate. Fixture-testable: YES, frob's own PII-structural gate and its own logging module.
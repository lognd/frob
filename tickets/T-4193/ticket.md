---
id: T-4193
title: 'playbook: a failure-injection repro test must assert every field of the response,
  not only the test-plan''s named field'
state: queued
kind: docs
origin: agent
created: '2026-09-07'
priority: low
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-307/H3-6 (T-4109): a process rule, not a code rule -- a test-plan row written as 'reports db and redis' was satisfied literally while a roll-up field stayed constant. Extends the prior audit's failing-dependency rule to cover every field of the response, not just the one named. Not fixture-testable as code; document the convention.
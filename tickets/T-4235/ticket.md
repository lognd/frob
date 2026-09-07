---
id: T-4235
title: a blanket waiver over a whole node/file must not silently excuse unrelated
  concerns beyond its stated reason
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
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
Consumer F-325/H2-2 second half: a waiver reasoning 'the REL201 proof reads Python only, permanent until frob scans shell' covers a whole node's exec capability, silently also excusing timeout hygiene, argv-secret hygiene, and parsing correctness in the one script standing between the business and total data loss -- far more than its stated reason justifies. Distinct from T-3994 (SEV001, severity-override accountability) and T-4214 (branch-condition waiver-premise expiry, same file, filed under T-4157) -- this is a third, distinct waiver-hygiene defect: SCOPE overreach rather than missing accountability or an unchecked premise. Fixture-testable: YES, frob's own waiver DSL.
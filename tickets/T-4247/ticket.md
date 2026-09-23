---
id: T-4247
title: a test bound as evidence that SKIPPED in the measured run must be reported
  with its skip reason recorded in the ledger
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
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
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: sprint
  old_value: v0.540.0
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
Consumer F-326/M2-8: a round-1 rule (a test bound as evidence that SKIPPED in the measured run is reported, not silently counted) is still unimplemented; this is its second sighting, strengthened -- the skip reason itself (e.g. an env-var skip hatch) must be recorded WITH the evidence, so the skip condition is visible in the ledger rather than only in scrolled-past test output. Fixture-testable: YES, frob's own evidence/test-collection mechanism.
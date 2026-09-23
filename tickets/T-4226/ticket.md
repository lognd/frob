---
id: T-4226
title: 'cross-artifact producer/consumer check: a value one script writes and another
  parses must be verified as one contract, not per-half unit tests'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4175
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
Consumer F-373/P1 (T-4175): a shell script POSTs a header, a backend route's unit tests construct that header themselves, and a separate ops test asserts only on the payload -- both halves pass in isolation and no gate compares producer against consumer. Not fixture-testable in frob's own tree: no shell-to-backend script pairing exists here.
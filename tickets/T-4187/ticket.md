---
id: T-4187
title: 'DRIFT: compare a module''s own docstring against its own module''s code, not
  only doc files against acked refs'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4109
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
- src/frob/gates/_docblocks.py
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
Consumer F-307/H3-9 (T-4109). Distinct comparison target from the claim-lint leaf (T-4185's sibling): DRIFT001 today compares doc FILES to acked refs and never a module docstring's own claim against that module's code. Do not collapse with H3-4 per the epic's instruction. Fixture-testable: YES.
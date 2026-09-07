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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docblocks.py
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
Consumer F-307/H3-9 (T-4109). Distinct comparison target from the claim-lint leaf (T-4185's sibling): DRIFT001 today compares doc FILES to acked refs and never a module docstring's own claim against that module's code. Do not collapse with H3-4 per the epic's instruction. Fixture-testable: YES.
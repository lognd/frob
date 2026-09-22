---
id: T-5282
title: 'Post-land sweep residue 2026-09-22_0556: COV002:src/frob/tickets/_flow.py
  COV002:tests/test_gates_fix_engine.py COV002:tests/test_tickets_points.py COV007:src/frob/tickets/_flow.py '
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: v0.540.0
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
  at: '2026-09-22'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Findings raised by a post-land sweep and disposed against this ticket by the coordinator's runner to keep the quarantine clear. Fix each in scope:
COV002:src/frob/tickets/_flow.py
COV002:tests/test_gates_fix_engine.py
COV002:tests/test_tickets_points.py
COV007:src/frob/tickets/_flow.py
DUP001:tests/test_tickets_points.py
FLAGCOV001:frob.toml
WIRE001:src/frob/_cli_parsers/_ticket/_metadata.py
WIRE001:src/frob/_cli_parsers/_ticket/_new.py
WIRE001:src/frob/_cli_parsers/_ticket/_progress.py
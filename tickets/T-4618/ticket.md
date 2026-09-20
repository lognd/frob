---
id: T-4618
title: 'Clean docstrings: test_tickets/gate_cache/land_finish/pii/lang/ci_matrix/priority
  (DOCARCH001)'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: medium
parent: T-4421
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_tickets.py
- tests/test_gate_cache.py
- tests/test_ticket_work_and_land_finish.py
- tests/test_lang.py
- tests/test_ci_workflow_matrix.py
- tests/test_tickets_priority.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/test_pii_structural_gate.py
  reason: leased by in-progress T-4073, skip to avoid cross-ticket collision
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: parent
  old_value: null
  new_value: T-4421
  reason: child of T-4421 docarch debloat split
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given a frob check scoped to these 7 files, when DOCARCH001 is measured, then
    the combined finding count is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-4421 (debloat sprint v0.534.0). Measured 2026-09-19: DOCARCH001 finding count for these 7 files was 29 (5+5+4+4+4+4+3) on a truncated repo-wide check; re-measure per-file before starting, the run that produced this count did not finish and may be an undercount. Rewrite each flagged docstring to state WHAT the symbol/test does; move any narrative worth keeping into the ticket that made the change via 'frob ticket body <id> --append'. Do not touch files leased by another in-progress ticket.
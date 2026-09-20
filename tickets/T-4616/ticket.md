---
id: T-4616
title: 'Clean docstrings: test_ticket_leases/hook_frob_suggest/graph (DOCARCH001)'
state: dropped
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
- tests/test_ticket_leases.py
- tests/test_hook_frob_suggest.py
- tests/test_graph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
- text: Given a frob check scoped to tests/test_ticket_leases.py, tests/test_hook_frob_suggest.py,
    tests/test_graph.py, when DOCARCH001 is measured, then the combined finding count
    is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-4421 (debloat sprint v0.534.0). Measured 2026-09-19: DOCARCH001 finding count for these 3 files was 27 (13+7+7) on a truncated repo-wide check; re-measure per-file before starting, the run that produced this count did not finish and may be an undercount. Rewrite each flagged docstring to state WHAT the symbol/test does; move any narrative worth keeping into the ticket that made the change via 'frob ticket body <id> --append'. Do not touch files leased by another in-progress ticket.

## Drop reason
- 2026-09-20: exact duplicate DOCARCH001 cluster filing; the leased copy T-4625 carries the work (sprint triage drop, direction corrected) (absorbed by T-4625)

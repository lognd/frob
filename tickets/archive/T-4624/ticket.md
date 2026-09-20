---
id: T-4624
title: 'Clean docstrings: test_tickets_acceptance/refs_gate/hook_root_write_guard/docptr/check_runner/scan_tree/etc
  (DOCARCH001)'
state: done
kind: docs
origin: agent
created: '2026-09-19'
priority: medium
parent: T-4421
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_tickets_acceptance.py
- tests/test_refs_gate.py
- tests/test_hook_root_write_guard.py
- tests/test_docptr_gate.py
- tests/test_check_runner.py
- tests/vet_suite/test_scan_tree.py
- tests/test_tickets_evidence_cli.py
- tests/test_refactor.py
- tests/test_perf.py
- tests/test_land_verify_claims_outcome.py
- tests/test_hook_frob_timeout_guard.py
- tests/test_gates_suppress.py
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
evidence:
- tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_ticket_plus_narrative_wording_warns
designated_repro_test: null
acceptance:
- text: Given a frob check scoped to these 12 files, when DOCARCH001 is measured,
    then the combined finding count is 0
  evidence:
  - tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_ticket_plus_narrative_wording_warns
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-4421 (debloat sprint v0.534.0). Measured 2026-09-19: DOCARCH001 finding count for these 12 files was 29 (3+3+3+3+3+2+2+2+2+2+2+2) on a truncated repo-wide check; re-measure per-file before starting, the run that produced this count did not finish and may be an undercount. Rewrite each flagged docstring to state WHAT the symbol/test does; move any narrative worth keeping into the ticket that made the change via 'frob ticket body <id> --append'. Do not touch files leased by another in-progress ticket.
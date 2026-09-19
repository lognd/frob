---
id: T-0557
title: 'gates: TEST005 silently skips symbols absent from coverage.xml (B4)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0403
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: moving DOCARCH001 change-narrative out of the test docstring per T-4420
  actor: logan
  at: '2026-09-19'
  old_length: 494
  new_length: 1070
evidence:
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test005_unmeasured_symbol_in_measured_file_flags_as_zero
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test005_symbol_in_unmeasured_file_still_skipped
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
docs/audits/gates-accounting.md B4. _test005_symbols: pct = data.symbol_branch.get(record.symref); skipped (not flagged) when pct is None, i.e. when the symbol was never executed at all -- coverage.xml has no row for it. Combined with B1, completely dead public code clears both TEST001 (name match) and TEST005 (no data). RIGHT-WAY fix: a public symbol with NO coverage record at all should be treated as 0% (flag), not skipped -- distinguish 'never executed' from 'excluded from measurement'.

DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_test_gate.py::TestTestGate.test_test005_unmeasured_symbol_in_measured_file_flags_as_zero's docstring used to say: 'T-0557 (B4): a symbol with NO entry in symbol_branch -- never executed at all -- must still be flagged at 0% branch coverage when its FILE genuinely was measured (has a module_line entry). Previously _test005_symbols skipped any symbol absent from symbol_branch, silently clearing dead code that a test suite never calls into even once.' Moved here; the test docstring now states only what it verifies.
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
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test005_unmeasured_symbol_in_measured_file_flags_as_zero
- tests/test_gates.py::TestTestGate::test_test005_symbol_in_unmeasured_file_still_skipped
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B4. _test005_symbols: pct = data.symbol_branch.get(record.symref); skipped (not flagged) when pct is None, i.e. when the symbol was never executed at all -- coverage.xml has no row for it. Combined with B1, completely dead public code clears both TEST001 (name match) and TEST005 (no data). RIGHT-WAY fix: a public symbol with NO coverage record at all should be treated as 0% (flag), not skipped -- distinguish 'never executed' from 'excluded from measurement'.
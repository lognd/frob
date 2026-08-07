---
id: T-0525
title: COV006 waiver granularity is file-scoped, not symbol-scoped -- can silently
  over-waive
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: COV006 symref regression tests + splitting the file-blanket TestProcessPoolGates/TestGateOrderSetEquality
    waivers into per-test waivers
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov006_violation_carries_edge_src_as_symref
- tests/test_gates.py::TestCoverageGate::test_cov006_waiver_does_not_blanket_suppress_the_whole_file
designated_repro_test: null
threat: null
component: null
---
Discovered while working T-0516: COV006 Violation objects carry no symref (file=test_file, line=0), so _match_waiver falls back to file-level matching for a frob:waive COV006 comment anywhere in that file -- ANY single COV006 waiver in a test file silently suppresses EVERY COV006 finding in that file, not just the one it was written next to. Verified directly: adding one waiver comment near one test in tests/test_gates.py suppressed all 7 COV006 findings then present in that file, including unrelated ones that were NOT sound (an import-alias false-positive that needed a real fix, not a waiver). Consider giving COV006 violations a symref (the test's own qualname) so _match_waiver can do symbol-exact matching the way most other rules do, instead of falling back to file-scope for a rule that very plausibly has multiple independent findings per file.
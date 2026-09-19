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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: COV006 symref regression tests + splitting the file-blanket TestProcessPoolGates/TestGateOrderSetEquality
    waivers into per-test waivers
  actor: logan
  at: '2026-07-23'
body_changes:
- mode: append
  reason: moving DOCARCH001 change-narrative out of the test docstrings per T-4420
  actor: logan
  at: '2026-09-19'
  old_length: 858
  new_length: 1999
evidence:
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_violation_carries_edge_src_as_symref
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov006_waiver_does_not_blanket_suppress_the_whole_file
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Discovered while working T-0516: COV006 Violation objects carry no symref (file=test_file, line=0), so _match_waiver falls back to file-level matching for a frob:waive COV006 comment anywhere in that file -- ANY single COV006 waiver in a test file silently suppresses EVERY COV006 finding in that file, not just the one it was written next to. Verified directly: adding one waiver comment near one test in tests/test_gates.py suppressed all 7 COV006 findings then present in that file, including unrelated ones that were NOT sound (an import-alias false-positive that needed a real fix, not a waiver). Consider giving COV006 violations a symref (the test's own qualname) so _match_waiver can do symbol-exact matching the way most other rules do, instead of falling back to file-scope for a rule that very plausibly has multiple independent findings per file.

DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_coverage.py has two tests citing this ticket's own change-narrative in their docstrings (test_cov006_violation_carries_edge_src_as_symref and test_cov006_waiver_does_not_blanket_suppress_the_whole_file). Original text: (1) 'T-0525: a COV006 finding's symref is the offending frob:tests edge's own src (the test's symref), not None -- this is what lets _match_waiver do symbol-exact matching instead of falling back to file-scope, where a single waiver anywhere in the file used to silently suppress every COV006 finding in it (T-0148's precedent for TEST005, applied here).' (2) 'T-0525 regression: two independent, unsound frob:tests edges in the SAME test file each produce their own COV006 finding; a frob:waive COV006 comment bound to only ONE of the two tests must suppress only that one -- NOT both, the T-0148-class blanket-waiver bug this ticket fixes for COV006 specifically (previously verified live: one waiver comment in tests/test_gates.py silently absorbed all 7 COV006 findings then present in that file).' Moved here; both docstrings now state only what they verify.
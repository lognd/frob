---
id: T-0553
title: 'gates: file-level waiver blanket-suppresses every same-rule violation in the
  file (B11)'
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
  old_length: 638
  new_length: 1241
evidence:
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov001_waiver_does_not_blanket_suppress_sibling_symbol
- tests/gates_suite/test_coverage.py::TestCoverageGate::test_waiver_suppresses_and_reports
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
docs/audits/gates-accounting.md B11. _match_waiver: when violation.symref is None (COV001/COV002/DRIFT/most rules) a waiver matches on file alone, so one frob:waive COV002 anywhere in a file waives ALL changed-symbol accounting violations for every symbol in that file; a package-prefix waiver can waive a whole package's TEST003/004 requirement. Only TEST005 sets symref for symbol-exact matching. Fix direction: set symref on more violation kinds (COV001/002, INV001, etc, wherever a specific symbol is the actual subject) so waivers narrow to symbol-exact by default, reserving file/package blast radius for genuinely file-level rules.

DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_coverage.py::TestCoverageGate.test_cov001_waiver_does_not_blanket_suppress_sibling_symbol's docstring used to say: 'T-0553 (B11): a frob:waive COV001 placed above ONE public symbol must not also suppress COV001 for a DIFFERENT public symbol in the same file -- before this fix, COV001's Violation carried no symref, so _match_waiver fell back to file-scoped matching and one directive silently waived every undocumented symbol in the file, not just the one it was written above.' Moved here; the test docstring now states only what it verifies.
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
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov001_waiver_does_not_blanket_suppress_sibling_symbol
- tests/test_gates.py::TestCoverageGate::test_waiver_suppresses_and_reports
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B11. _match_waiver: when violation.symref is None (COV001/COV002/DRIFT/most rules) a waiver matches on file alone, so one frob:waive COV002 anywhere in a file waives ALL changed-symbol accounting violations for every symbol in that file; a package-prefix waiver can waive a whole package's TEST003/004 requirement. Only TEST005 sets symref for symbol-exact matching. Fix direction: set symref on more violation kinds (COV001/002, INV001, etc, wherever a specific symbol is the actual subject) so waivers narrow to symbol-exact by default, reserving file/package blast radius for genuinely file-level rules.
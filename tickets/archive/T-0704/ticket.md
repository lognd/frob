---
id: T-0704
title: T-0265 evidence no longer resolves -- test class removed from tests/test_gates.py,
  COV003 fires on every full check
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestSelfReferentialTestsDirectiveScopeAgreement::test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff
designated_repro_test: null
threat: null
component: null
---
Found while working T-0340 (native-rebuild Makefile guard, unrelated). frob check (full, not --ticket-scoped) fires COV003 for tickets/T-0265:0 -- the recorded evidence id tests/test_gates.py::TestSelfReferentialTestsDirectiveScopeAgreement::test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff no longer exists anywhere in tests/test_gates.py (grep confirms zero hits), even though T-0265's ledger state is done. Either the test was renamed/removed without updating the evidence id, or T-0265's Done report evidence was never accurate post-some-later-refactor. Fix: locate the current equivalent test (if the behavior is still tested under a new name) and update T-0265's evidence id, or re-open T-0265 if the behavior regressed.
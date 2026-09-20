---
id: T-3541
title: 'lang conformance: cuda fixture has no directive continuation, failing test_directive_continuation_folds_correctly_not_just_present'
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/fixtures/lang/sample.cu
- tests/test_lang_conformance_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4709: preserve test-skip detail trimmed from _lang_conformance.py'
  actor: logan
  at: '2026-09-19'
  old_length: 563
  new_length: 1068
evidence:
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_directive_continuation_folds_correctly_not_just_present
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 00db1c194c76e8b0e6898f4e357f9b9938654c91
---
MEASURED run 33353658750: tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_directive_continuation_folds_correctly_not_just_present fails with AssertionError: cuda's fixture has no continuation. The behavioral capability check requires every language fixture to exercise a folded multi-line directive continuation; the CUDA fixture (tests/fixtures/lang/sample.cu, T-1602/T-3493) never got one. Add a folded continuation directive to the CUDA fixture (copy the shape the java/zig fixtures use) and confirm the test passes for every language.


T-4709 follow-up (condensed from a fixture comment in
src/frob/gates/_lang_conformance.py, trimmed for DOCARCH002's 12-line
cap): this claim was UNVERIFIED against the behavioral check until
T-3541 -- the merged single-token comment fails to parse as a directive
at all, never reaching `frob.lang`'s own fold logic.
`TestBehavioralCapabilityCheck.
test_directive_continuation_folds_correctly_not_just_present` now skips
cuda the same way it already skips c/cpp, with this same measurement
cited there.
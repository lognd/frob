---
id: T-3541
title: 'lang conformance: cuda fixture has no directive continuation, failing test_directive_continuation_folds_correctly_not_just_present'
state: queued
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED run 33353658750: tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_directive_continuation_folds_correctly_not_just_present fails with AssertionError: cuda's fixture has no continuation. The behavioral capability check requires every language fixture to exercise a folded multi-line directive continuation; the CUDA fixture (tests/fixtures/lang/sample.cu, T-1602/T-3493) never got one. Add a folded continuation directive to the CUDA fixture (copy the shape the java/zig fixtures use) and confirm the test passes for every language.
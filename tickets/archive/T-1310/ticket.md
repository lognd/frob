---
id: T-1310
title: 'TEST005 burn-down: src/frob/arch (87 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- tests/arch/**
- src/frob/arch/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/arch/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/arch/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/test_arch_gate.py::TestArchComplexityAware::test_flat_long_function_not_flagged
- tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
designated_repro_test: null
acceptance:
- text: GIVEN the arch package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/arch/**
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
  - tests/test_arch_gate.py::TestArchComplexityAware::test_flat_long_function_not_flagged
  - tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
- text: GIVEN a 0.0%-branch symbol in arch WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
  - tests/test_arch_gate.py::TestArchComplexityAware::test_flat_long_function_not_flagged
  - tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
- text: GIVEN a new test added to close a arch TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
  - tests/test_arch_gate.py::TestArchComplexityAware::test_flat_long_function_not_flagged
  - tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
threat: null
component: null
---
Package: src/frob/arch (or the listed root modules).
TEST005 findings at current baseline: 87 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
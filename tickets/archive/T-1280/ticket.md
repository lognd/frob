---
id: T-1280
title: 'TEST005 burn-down: src/frob/fuzz (19 findings, 11 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/fuzz/**
- tests/fuzz/**
- tests/test_fuzz.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_fuzz.py
  reason: existing test file convention is tests/test_fuzz.py, not tests/fuzz/
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_fuzz.py::TestStamp::test_malformed_json_stamp_is_none
- tests/test_fuzz.py::TestStamp::test_non_dict_json_stamp_is_none
- tests/test_fuzz.py::TestStamp::test_write_failure_returns_stamp_failed
- tests/test_fuzz.py::TestResolve::test_resolve_without_hypothesis_installed_is_no_generator
- tests/test_fuzz.py::TestResolve::test_pydantic_derivation_failure_is_no_generator
designated_repro_test: null
acceptance:
- text: GIVEN the fuzz package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/fuzz/**
  evidence:
  - tests/test_fuzz.py::TestStamp::test_malformed_json_stamp_is_none
  - tests/test_fuzz.py::TestStamp::test_non_dict_json_stamp_is_none
  - tests/test_fuzz.py::TestStamp::test_write_failure_returns_stamp_failed
  - tests/test_fuzz.py::TestResolve::test_resolve_without_hypothesis_installed_is_no_generator
  - tests/test_fuzz.py::TestResolve::test_pydantic_derivation_failure_is_no_generator
- text: GIVEN a 0.0%-branch symbol in fuzz WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/test_fuzz.py::TestStamp::test_malformed_json_stamp_is_none
  - tests/test_fuzz.py::TestStamp::test_non_dict_json_stamp_is_none
  - tests/test_fuzz.py::TestStamp::test_write_failure_returns_stamp_failed
  - tests/test_fuzz.py::TestResolve::test_resolve_without_hypothesis_installed_is_no_generator
  - tests/test_fuzz.py::TestResolve::test_pydantic_derivation_failure_is_no_generator
- text: GIVEN a new test added to close a fuzz TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/test_fuzz.py::TestStamp::test_malformed_json_stamp_is_none
  - tests/test_fuzz.py::TestStamp::test_non_dict_json_stamp_is_none
  - tests/test_fuzz.py::TestStamp::test_write_failure_returns_stamp_failed
  - tests/test_fuzz.py::TestResolve::test_resolve_without_hypothesis_installed_is_no_generator
  - tests/test_fuzz.py::TestResolve::test_pydantic_derivation_failure_is_no_generator
threat: null
component: null
---
Package: src/frob/fuzz (or the listed root modules).
TEST005 findings at current baseline: 19 total, 11 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_rules.py :: FUZZ001
_rules.py :: FUZZ002
_rules.py :: FUZZ003
_obligations.py :: obligations
_run.py :: run_fuzz
_signatures.py :: resolve_param_types
_stamp.py :: stamp_fuzz
_stamp.py :: load_fuzz_stamp
_arbitrary.py :: FuzzRegistry.register
_arbitrary.py :: register
_arbitrary.py :: resolve

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
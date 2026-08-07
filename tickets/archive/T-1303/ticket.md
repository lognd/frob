---
id: T-1303
title: 'TEST005 burn-down: src/frob/mutate (17 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/mutate/**
- tests/mutate/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_mutate.py::test_generate_mutants_covers_operators
- tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content
- tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
designated_repro_test: null
acceptance:
- text: GIVEN the mutate package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/mutate/**
  evidence:
  - tests/test_mutate.py::test_generate_mutants_covers_operators
  - tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content
  - tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
- text: GIVEN a 0.0%-branch symbol in mutate WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content
- text: GIVEN a new test added to close a mutate TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/test_mutate.py::test_generate_mutants_covers_operators
  - tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content
  - tests/integration/test_mutate_runner.py::TestMutateRunnerJson::test_json_output_is_clean
threat: null
component: null
---
Package: src/frob/mutate (or the listed root modules).
TEST005 findings at current baseline: 17 total, 0 at exactly
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
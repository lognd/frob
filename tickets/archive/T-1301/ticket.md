---
id: T-1301
title: 'TEST005 burn-down: src/frob/process (37 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/process/**
- tests/process/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_process.py::test_pytest_all_pass
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir
- tests/unit/test_process_guard.py::TestExecEnabled::test_unset_env_is_enabled
designated_repro_test: null
acceptance:
- text: GIVEN the process package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/process/**
  evidence:
  - tests/unit/test_process.py::test_pytest_all_pass
  - tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir
  - tests/unit/test_process_guard.py::TestExecEnabled::test_unset_env_is_enabled
- text: GIVEN a 0.0%-branch symbol in process WHEN it is judged dead code THEN it
    is routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir
- text: GIVEN a new test added to close a process TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_process.py::test_pytest_all_pass
  - tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir
  - tests/unit/test_process_guard.py::TestExecEnabled::test_unset_env_is_enabled
threat: null
component: null
---
Package: src/frob/process (or the listed root modules).
TEST005 findings at current baseline: 37 total, 0 at exactly
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
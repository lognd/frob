---
id: T-1291
title: 'TEST005 burn-down: src/frob/bind (4 findings, 3 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/bind/**
- tests/bind/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_bind.py::test_scan_bindings_finds_cpp_and_rust
- tests/unit/test_bind.py::test_scan_sources_finds_header_and_rust
- tests/unit/test_bind.py::test_check_reports_mismatch_for_unbound_binding
designated_repro_test: null
acceptance:
- text: GIVEN the bind package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/bind/**
  evidence:
  - tests/unit/test_bind.py::test_scan_bindings_finds_cpp_and_rust
  - tests/unit/test_bind.py::test_scan_sources_finds_header_and_rust
  - tests/unit/test_bind.py::test_check_reports_mismatch_for_unbound_binding
- text: GIVEN a 0.0%-branch symbol in bind WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_bind.py::test_scan_bindings_finds_cpp_and_rust
  - tests/unit/test_bind.py::test_scan_sources_finds_header_and_rust
  - tests/unit/test_bind.py::test_check_reports_mismatch_for_unbound_binding
- text: GIVEN a new test added to close a bind TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_bind.py::test_scan_bindings_finds_cpp_and_rust
  - tests/unit/test_bind.py::test_scan_sources_finds_header_and_rust
  - tests/unit/test_bind.py::test_check_reports_mismatch_for_unbound_binding
threat: null
component: null
---
Package: src/frob/bind (or the listed root modules).
TEST005 findings at current baseline: 4 total, 3 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
__init__.py :: scan_bindings
__init__.py :: scan_sources
__init__.py :: check

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
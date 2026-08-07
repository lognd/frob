---
id: T-1308
title: 'TEST005 burn-down: src/frob/cve (3 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/cve/**
- tests/cve/**
- tests/unit/cve/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/cve/**
  reason: real test dir differs from ticket's guessed tests/cve/** glob
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/cve/test_parser.py::test_parse_truncated_json
- tests/unit/cve/test_parser.py::test_parse_rejected_record
- tests/unit/cve/test_parser.py::test_iter_mirror_yields_records_and_errors
- tests/unit/cve/test_vet_match.py::test_log4shell_end_to_end_cwe_linkage_via_mirror
designated_repro_test: null
acceptance:
- text: GIVEN the cve package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/cve/**
  evidence:
  - tests/unit/cve/test_parser.py::test_parse_truncated_json
  - tests/unit/cve/test_parser.py::test_parse_rejected_record
  - tests/unit/cve/test_parser.py::test_iter_mirror_yields_records_and_errors
  - tests/unit/cve/test_vet_match.py::test_log4shell_end_to_end_cwe_linkage_via_mirror
- text: GIVEN a 0.0%-branch symbol in cve WHEN it is judged dead code THEN it is routed
    to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/cve/test_parser.py::test_parse_truncated_json
  - tests/unit/cve/test_parser.py::test_parse_rejected_record
  - tests/unit/cve/test_parser.py::test_iter_mirror_yields_records_and_errors
  - tests/unit/cve/test_vet_match.py::test_log4shell_end_to_end_cwe_linkage_via_mirror
- text: GIVEN a new test added to close a cve TEST005 finding WHEN reviewed THEN it
    asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/cve/test_parser.py::test_parse_truncated_json
  - tests/unit/cve/test_parser.py::test_parse_rejected_record
  - tests/unit/cve/test_parser.py::test_iter_mirror_yields_records_and_errors
  - tests/unit/cve/test_vet_match.py::test_log4shell_end_to_end_cwe_linkage_via_mirror
threat: null
component: null
---
Package: src/frob/cve (or the listed root modules).
TEST005 findings at current baseline: 3 total, 0 at exactly
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
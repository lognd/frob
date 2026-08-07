---
id: T-1302
title: 'TEST005 burn-down: src/frob/outline (4 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/outline/**
- tests/outline/**
- tests/unit/test_outline.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_outline.py
  reason: real test file location differs from the ticket's guessed tests/outline/**
    glob
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_outline.py::test_py_outline_parse_failed_when_source_over_size_cap
- tests/unit/test_outline.py::test_py_outline_as_text_hides_private_and_shows_docs
- tests/unit/test_outline.py::test_py_outline_nested_class_method_has_no_top_level_owner
- tests/unit/test_outline.py::test_py_outline_doc_with_no_period_uses_80_char_fallback
- tests/unit/test_outline.py::test_py_outline_dedupes_repeated_import_root
designated_repro_test: null
acceptance:
- text: GIVEN the outline package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/outline/**
  evidence:
  - tests/unit/test_outline.py::test_py_outline_parse_failed_when_source_over_size_cap
  - tests/unit/test_outline.py::test_py_outline_as_text_hides_private_and_shows_docs
  - tests/unit/test_outline.py::test_py_outline_nested_class_method_has_no_top_level_owner
  - tests/unit/test_outline.py::test_py_outline_doc_with_no_period_uses_80_char_fallback
  - tests/unit/test_outline.py::test_py_outline_dedupes_repeated_import_root
- text: GIVEN a 0.0%-branch symbol in outline WHEN it is judged dead code THEN it
    is routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_outline.py::test_py_outline_parse_failed_when_source_over_size_cap
  - tests/unit/test_outline.py::test_py_outline_as_text_hides_private_and_shows_docs
  - tests/unit/test_outline.py::test_py_outline_nested_class_method_has_no_top_level_owner
  - tests/unit/test_outline.py::test_py_outline_doc_with_no_period_uses_80_char_fallback
  - tests/unit/test_outline.py::test_py_outline_dedupes_repeated_import_root
- text: GIVEN a new test added to close a outline TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_outline.py::test_py_outline_parse_failed_when_source_over_size_cap
  - tests/unit/test_outline.py::test_py_outline_as_text_hides_private_and_shows_docs
  - tests/unit/test_outline.py::test_py_outline_nested_class_method_has_no_top_level_owner
  - tests/unit/test_outline.py::test_py_outline_doc_with_no_period_uses_80_char_fallback
  - tests/unit/test_outline.py::test_py_outline_dedupes_repeated_import_root
threat: null
component: null
---
Package: src/frob/outline (or the listed root modules).
TEST005 findings at current baseline: 4 total, 0 at exactly
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
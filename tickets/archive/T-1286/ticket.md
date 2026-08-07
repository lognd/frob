---
id: T-1286
title: 'TEST005 burn-down: src/frob/docs (5 findings, 4 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/docs/**
- tests/docs/**
- tests/unit/test_docs_module.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_docs_module.py
  reason: tests actually live under tests/unit/test_docs_module.py, not tests/docs/**
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/app.md
  reason: doc targets for these symbols live in docs/modules/app.md (shared across
    the app package); no doc content change is planned, only scope closure
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_docs_module.py::test_extract_docstrings_non_python_file_returns_empty
- tests/unit/test_docs_module.py::test_extract_docstrings_parse_failure_returns_empty
- tests/unit/test_docs_module.py::test_extract_docstrings_symbol_filter_narrows_to_one_method
- tests/unit/test_docs_module.py::test_find_docs_dir_not_found_returns_none
- tests/unit/test_docs_module.py::test_overview_no_keyword_match_falls_back_to_all_entries
- tests/unit/test_docs_module.py::test_overview_symbol_keyword_narrows_match
- tests/unit/test_docs_module.py::test_search_tracks_heading_and_joins_surrounding_lines
designated_repro_test: null
acceptance:
- text: GIVEN the docs package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/docs/**
  evidence:
  - tests/unit/test_docs_module.py::test_extract_docstrings_non_python_file_returns_empty
  - tests/unit/test_docs_module.py::test_extract_docstrings_parse_failure_returns_empty
  - tests/unit/test_docs_module.py::test_extract_docstrings_symbol_filter_narrows_to_one_method
  - tests/unit/test_docs_module.py::test_find_docs_dir_not_found_returns_none
  - tests/unit/test_docs_module.py::test_overview_no_keyword_match_falls_back_to_all_entries
  - tests/unit/test_docs_module.py::test_overview_symbol_keyword_narrows_match
  - tests/unit/test_docs_module.py::test_search_tracks_heading_and_joins_surrounding_lines
- text: GIVEN a 0.0%-branch symbol in docs WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_docs_module.py::test_extract_docstrings_symbol_filter_narrows_to_one_method
- text: GIVEN a new test added to close a docs TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_docs_module.py::test_extract_docstrings_non_python_file_returns_empty
  - tests/unit/test_docs_module.py::test_extract_docstrings_parse_failure_returns_empty
  - tests/unit/test_docs_module.py::test_extract_docstrings_symbol_filter_narrows_to_one_method
  - tests/unit/test_docs_module.py::test_find_docs_dir_not_found_returns_none
  - tests/unit/test_docs_module.py::test_overview_no_keyword_match_falls_back_to_all_entries
  - tests/unit/test_docs_module.py::test_overview_symbol_keyword_narrows_match
  - tests/unit/test_docs_module.py::test_search_tracks_heading_and_joins_surrounding_lines
threat: null
component: null
---
Package: src/frob/docs (or the listed root modules).
TEST005 findings at current baseline: 5 total, 4 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
__init__.py :: extract_docstrings
__init__.py :: find_docs_dir
__init__.py :: overview
__init__.py :: search

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
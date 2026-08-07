---
id: T-1289
title: 'TEST005 burn-down: src/frob/map (4 findings, 3 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/map/**
- tests/map/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_map.py::test_map_finds_all_files
- tests/unit/test_map.py::test_map_totals
- tests/unit/test_map.py::test_map_symbols_populated
- tests/unit/test_map.py::test_map_depth_limits_recursion
- tests/unit/test_map.py::test_map_as_text
- tests/unit/test_map.py::test_map_as_json
designated_repro_test: null
acceptance:
- text: GIVEN the map package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/map/**
  evidence:
  - tests/unit/test_map.py::test_map_finds_all_files
  - tests/unit/test_map.py::test_map_totals
  - tests/unit/test_map.py::test_map_symbols_populated
  - tests/unit/test_map.py::test_map_depth_limits_recursion
  - tests/unit/test_map.py::test_map_as_text
  - tests/unit/test_map.py::test_map_as_json
- text: GIVEN a 0.0%-branch symbol in map WHEN it is judged dead code THEN it is routed
    to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_map.py::test_map_finds_all_files
  - tests/unit/test_map.py::test_map_totals
  - tests/unit/test_map.py::test_map_symbols_populated
  - tests/unit/test_map.py::test_map_depth_limits_recursion
  - tests/unit/test_map.py::test_map_as_text
  - tests/unit/test_map.py::test_map_as_json
- text: GIVEN a new test added to close a map TEST005 finding WHEN reviewed THEN it
    asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_map.py::test_map_finds_all_files
  - tests/unit/test_map.py::test_map_totals
  - tests/unit/test_map.py::test_map_symbols_populated
  - tests/unit/test_map.py::test_map_depth_limits_recursion
  - tests/unit/test_map.py::test_map_as_text
  - tests/unit/test_map.py::test_map_as_json
threat: null
component: null
---
Package: src/frob/map (or the listed root modules).
TEST005 findings at current baseline: 4 total, 3 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
__init__.py :: MapResult.as_text
__init__.py :: MapResult.as_json
__init__.py :: map_project

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
---
id: T-1282
title: 'TEST005 burn-down: src/frob/clean (10 findings, 6 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/clean/**
- tests/clean/**
- tests/test_clean.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_clean.py
  reason: existing test file convention is tests/test_clean.py, not tests/clean/
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_clean.py::test_reclaimed_bytes_sums_matched_entries
- tests/test_clean.py::test_reclaimed_bytes_is_zero_for_no_matches
designated_repro_test: null
acceptance:
- text: GIVEN the clean package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/clean/**
  evidence:
  - tests/test_clean.py::test_reclaimed_bytes_sums_matched_entries
  - tests/test_clean.py::test_reclaimed_bytes_is_zero_for_no_matches
- text: GIVEN a 0.0%-branch symbol in clean WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/test_clean.py::test_reclaimed_bytes_is_zero_for_no_matches
- text: GIVEN a new test added to close a clean TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/test_clean.py::test_reclaimed_bytes_sums_matched_entries
threat: null
component: null
---
Package: src/frob/clean (or the listed root modules).
TEST005 findings at current baseline: 10 total, 6 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_models.py :: CleanReport.reclaimed_bytes
_models.py :: CleanReport.count
_rules.py :: tier_patterns
_rules.py :: extra_patterns_from_config
_core.py :: scan
_core.py :: clean

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
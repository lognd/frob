---
id: T-1284
title: 'TEST005 burn-down: src/frob/gitlog (5 findings, 4 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/gitlog/**
- tests/gitlog/**
- tests/unit/test_gitlog.py
- tests/unit/test_gitlog_rendering.py
- docs/commands/gitlog.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_gitlog.py
  reason: existing gitlog test files live at tests/unit/, not tests/gitlog/ (that
    path does not exist); adding new coverage there for TEST005 burn-down
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/unit/test_gitlog_rendering.py
  reason: existing gitlog test files live at tests/unit/, not tests/gitlog/ (that
    path does not exist); adding new coverage there for TEST005 burn-down
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/commands/gitlog.md
  reason: 'scope closure: existing frob:doc edges from src/frob/gitlog point here;
    not planning to edit, but keep closure clean'
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_gitlog.py::test_git_log
- tests/unit/test_gitlog.py::test_git_log_include_non_conventional_keeps_unknown_type
- tests/unit/test_gitlog.py::test_git_log_since_tag_form_uses_range_syntax
- tests/unit/test_gitlog.py::test_git_log_until_and_limit_filter_output
- tests/unit/test_gitlog.py::test_git_log_missing_git_binary_returns_empty_result
designated_repro_test: null
acceptance:
- text: GIVEN the gitlog package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/gitlog/**
  evidence:
  - tests/unit/test_gitlog.py::test_git_log
  - tests/unit/test_gitlog.py::test_git_log_include_non_conventional_keeps_unknown_type
  - tests/unit/test_gitlog.py::test_git_log_since_tag_form_uses_range_syntax
  - tests/unit/test_gitlog.py::test_git_log_until_and_limit_filter_output
  - tests/unit/test_gitlog.py::test_git_log_missing_git_binary_returns_empty_result
- text: GIVEN a 0.0%-branch symbol in gitlog WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_gitlog.py::test_git_log_include_non_conventional_keeps_unknown_type
- text: GIVEN a new test added to close a gitlog TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_gitlog.py::test_git_log
  - tests/unit/test_gitlog.py::test_git_log_include_non_conventional_keeps_unknown_type
  - tests/unit/test_gitlog.py::test_git_log_since_tag_form_uses_range_syntax
  - tests/unit/test_gitlog.py::test_git_log_until_and_limit_filter_output
  - tests/unit/test_gitlog.py::test_git_log_missing_git_binary_returns_empty_result
threat: null
component: null
---
Package: src/frob/gitlog (or the listed root modules).
TEST005 findings at current baseline: 5 total, 4 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
__init__.py :: GitLogResult.groups
__init__.py :: GitLogResult.as_json
__init__.py :: GitLogResult.as_text
__init__.py :: git_log

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
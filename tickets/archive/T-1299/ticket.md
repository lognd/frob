---
id: T-1299
title: 'TEST005 burn-down: src/frob/scaffold (15 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/scaffold/**
- tests/scaffold/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::test_creates_missing_and_updates_stale
- tests/unit/test_scaffold_project.py::test_render_project_writes_expected_files
- tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_marker_detection_true_for_old_recipe
designated_repro_test: null
acceptance:
- text: GIVEN the scaffold package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/scaffold/**
  evidence:
  - tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::test_creates_missing_and_updates_stale
  - tests/unit/test_scaffold_project.py::test_render_project_writes_expected_files
  - tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_marker_detection_true_for_old_recipe
- text: GIVEN a 0.0%-branch symbol in scaffold WHEN it is judged dead code THEN it
    is routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::test_creates_missing_and_updates_stale
- text: GIVEN a new test added to close a scaffold TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_scaffold_managed.py::TestApplyManagedBlocks::test_creates_missing_and_updates_stale
  - tests/unit/test_scaffold_project.py::test_render_project_writes_expected_files
  - tests/unit/test_scaffold_natives_shim.py::TestLegacyCoreCacheDrift::test_legacy_marker_detection_true_for_old_recipe
threat: null
component: null
---
Package: src/frob/scaffold (or the listed root modules).
TEST005 findings at current baseline: 15 total, 0 at exactly
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
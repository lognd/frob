---
id: T-1281
title: 'TEST005 burn-down: src/frob/release (11 findings, 10 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/release/**
- tests/release/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/test_release.py::test_load_manifest_missing_is_no_manifest
designated_repro_test: null
acceptance:
- text: GIVEN the release package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/release/**
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
  - tests/test_release.py::test_load_manifest_missing_is_no_manifest
- text: GIVEN a 0.0%-branch symbol in release WHEN it is judged dead code THEN it
    is routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
  - tests/test_release.py::test_load_manifest_missing_is_no_manifest
- text: GIVEN a new test added to close a release TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
  - tests/test_release.py::test_load_manifest_missing_is_no_manifest
threat: null
component: null
---
Package: src/frob/release (or the listed root modules).
TEST005 findings at current baseline: 11 total, 10 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
__init__.py :: manifest_path
__init__.py :: load_manifest
__init__.py :: stamp
__init__.py :: authoritative_version
__init__.py :: rewrite_pyproject_version
__init__.py :: changelog_skeleton_entry
__init__.py :: set_manifest_version
__init__.py :: diff_class
__init__.py :: required_version
__init__.py :: satisfies

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
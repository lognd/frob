---
id: T-1305
title: 'TEST005 burn-down: src/frob/lang (37 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/lang/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_primitives.py::test_resolve_local_import_python_package_init_branch
- tests/unit/test_lang_primitives.py::test_resolve_local_import_cpp_resolves_relative_to_file_dir
- tests/unit/test_lang_primitives.py::test_resolve_local_import_cpp_outside_root_is_none
- tests/unit/test_lang_primitives.py::test_resolve_local_import_unknown_language_is_none
designated_repro_test: null
acceptance:
- text: GIVEN the lang package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/lang/**
  evidence:
  - tests/unit/test_lang_primitives.py::test_resolve_local_import_python_package_init_branch
- text: GIVEN a 0.0%-branch symbol in lang WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/test_lang_primitives.py::test_resolve_local_import_python_package_init_branch
  - tests/unit/test_lang_primitives.py::test_resolve_local_import_cpp_resolves_relative_to_file_dir
  - tests/unit/test_lang_primitives.py::test_resolve_local_import_cpp_outside_root_is_none
  - tests/unit/test_lang_primitives.py::test_resolve_local_import_unknown_language_is_none
- text: GIVEN a new test added to close a lang TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/test_lang_primitives.py::test_resolve_local_import_python_package_init_branch
  - tests/unit/test_lang_primitives.py::test_resolve_local_import_cpp_resolves_relative_to_file_dir
  - tests/unit/test_lang_primitives.py::test_resolve_local_import_cpp_outside_root_is_none
  - tests/unit/test_lang_primitives.py::test_resolve_local_import_unknown_language_is_none
threat: null
component: null
---
Package: src/frob/lang (or the listed root modules).
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
---
id: T-1307
title: 'TEST005 burn-down: src/frob/dup (33 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/dup/**
- tests/dup/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup.py::TestCoreAvailable::test_import_error_returns_false_and_logs
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_validate_claim_rungs_flags_unregistered_rung
- tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_validate_claim_rungs_flags_clone_type_mismatch
- tests/unit/test_dup_legacy_cpp.py::test_iter_functions_cpp_yields_qualified_names
- tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_covers_bindings
- tests/unit/test_dup_legacy_cpp.py::test_serialize_cpp_body_normalizes_locals_strings_and_numbers
designated_repro_test: null
acceptance:
- text: 'GIVEN a TEST005 finding in src/frob/dup that is fixable from this

    worktree (not blocked by an unbuildable optional native dependency)

    WHEN frob check --only test runs THEN it reports 0 such findings under

    src/frob/dup/** -- findings blocked solely by z3-solver''s build failure

    (src/frob/dup/_pipeline/_smt.py) are tracked as a separate environment-

    blocked follow-up, not required for this ticket''s own closure.'
  evidence:
  - tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_validate_claim_rungs_flags_unregistered_rung
- text: GIVEN a 0.0%-branch symbol in dup WHEN it is judged dead code THEN it is routed
    to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/test_dup.py::TestCoreAvailable::test_import_error_returns_false_and_logs
  - tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_validate_claim_rungs_flags_unregistered_rung
  - tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_validate_claim_rungs_flags_clone_type_mismatch
  - tests/unit/test_dup_legacy_cpp.py::test_iter_functions_cpp_yields_qualified_names
  - tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_covers_bindings
  - tests/unit/test_dup_legacy_cpp.py::test_serialize_cpp_body_normalizes_locals_strings_and_numbers
- text: GIVEN a new test added to close a dup TEST005 finding WHEN reviewed THEN it
    asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/test_dup.py::TestCoreAvailable::test_import_error_returns_false_and_logs
  - tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_validate_claim_rungs_flags_unregistered_rung
  - tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness::test_validate_claim_rungs_flags_clone_type_mismatch
  - tests/unit/test_dup_legacy_cpp.py::test_iter_functions_cpp_yields_qualified_names
  - tests/unit/test_dup_legacy_cpp.py::test_collect_locals_cpp_covers_bindings
  - tests/unit/test_dup_legacy_cpp.py::test_serialize_cpp_body_normalizes_locals_strings_and_numbers
acceptance_amendments:
- op: replace
  index: 0
  old_text: GIVEN the dup package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/dup/**
  new_text: 'GIVEN a TEST005 finding in src/frob/dup that is fixable from this

    worktree (not blocked by an unbuildable optional native dependency)

    WHEN frob check --only test runs THEN it reports 0 such findings under

    src/frob/dup/** -- findings blocked solely by z3-solver''s build failure

    (src/frob/dup/_pipeline/_smt.py) are tracked as a separate environment-

    blocked follow-up, not required for this ticket''s own closure.'
  reason: 'Unsatisfiable by construction as worded: 2 of 4 real findings in this

    ticket''s scope closed with real behavioral tests, but the 4th

    (src/frob/dup/_pipeline/_smt.py module-line floor) is blocked by a

    build-environment limitation, not a code/test gap -- z3-solver fails to

    build in this worktree (LibError: Unable to build Z3), so its tests

    structurally skip and cannot raise coverage from inside this session. A

    "0 findings" criterion cannot be honestly satisfied while an external

    dependency''s build is broken; this mirrors the T-1418-class amendment

    already applied to this ticket''s sibling T-1279.

    '
  actor: logan
  at: '2026-08-03'
threat: null
component: null
---
Package: src/frob/dup (or the listed root modules).
TEST005 findings at current baseline: 33 total, 0 at exactly
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
---
id: T-1292
title: 'TEST005 burn-down: src/frob/policy (4 findings, 2 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/policy/**
- tests/policy/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_policy.py::TestRules::test_forbidden_import_fires
- tests/test_policy.py::TestRules::test_forbidden_import_passes_outside_glob
- tests/test_policy.py::TestRules::test_forbidden_import_malformed_missing_field
- tests/test_policy.py::TestRules::test_pattern_query_matches
- tests/test_policy.py::TestRules::test_pattern_bad_query_is_err
- tests/test_policy.py::TestRules::test_pattern_missing_query_file_is_err
- tests/test_policy.py::TestRules::test_norm_max_diff_lines_fires
- tests/test_policy.py::TestRules::test_norm_passes_under_limit
- tests/test_policy.py::TestRules::test_norm_malformed_missing_max_lines
- tests/test_policy.py::TestRules::test_no_frob_toml_is_ok_empty
designated_repro_test: null
acceptance:
- text: GIVEN the policy package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/policy/**
  evidence:
  - tests/test_policy.py::TestRules::test_forbidden_import_fires
  - tests/test_policy.py::TestRules::test_forbidden_import_passes_outside_glob
  - tests/test_policy.py::TestRules::test_forbidden_import_malformed_missing_field
  - tests/test_policy.py::TestRules::test_pattern_query_matches
  - tests/test_policy.py::TestRules::test_pattern_bad_query_is_err
  - tests/test_policy.py::TestRules::test_pattern_missing_query_file_is_err
  - tests/test_policy.py::TestRules::test_norm_max_diff_lines_fires
  - tests/test_policy.py::TestRules::test_norm_passes_under_limit
  - tests/test_policy.py::TestRules::test_norm_malformed_missing_max_lines
  - tests/test_policy.py::TestRules::test_no_frob_toml_is_ok_empty
- text: GIVEN a 0.0%-branch symbol in policy WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/test_policy.py::TestRules::test_forbidden_import_fires
  - tests/test_policy.py::TestRules::test_forbidden_import_passes_outside_glob
  - tests/test_policy.py::TestRules::test_forbidden_import_malformed_missing_field
  - tests/test_policy.py::TestRules::test_pattern_query_matches
  - tests/test_policy.py::TestRules::test_pattern_bad_query_is_err
  - tests/test_policy.py::TestRules::test_pattern_missing_query_file_is_err
  - tests/test_policy.py::TestRules::test_norm_max_diff_lines_fires
  - tests/test_policy.py::TestRules::test_norm_passes_under_limit
  - tests/test_policy.py::TestRules::test_norm_malformed_missing_max_lines
  - tests/test_policy.py::TestRules::test_no_frob_toml_is_ok_empty
- text: GIVEN a new test added to close a policy TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/test_policy.py::TestRules::test_forbidden_import_fires
  - tests/test_policy.py::TestRules::test_forbidden_import_passes_outside_glob
  - tests/test_policy.py::TestRules::test_forbidden_import_malformed_missing_field
  - tests/test_policy.py::TestRules::test_pattern_query_matches
  - tests/test_policy.py::TestRules::test_pattern_bad_query_is_err
  - tests/test_policy.py::TestRules::test_pattern_missing_query_file_is_err
  - tests/test_policy.py::TestRules::test_norm_max_diff_lines_fires
  - tests/test_policy.py::TestRules::test_norm_passes_under_limit
  - tests/test_policy.py::TestRules::test_norm_malformed_missing_max_lines
  - tests/test_policy.py::TestRules::test_no_frob_toml_is_ok_empty
threat: null
component: null
---
Package: src/frob/policy (or the listed root modules).
TEST005 findings at current baseline: 4 total, 2 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
__init__.py :: load_policy
__init__.py :: policy_gate

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.
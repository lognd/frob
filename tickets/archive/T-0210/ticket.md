---
id: T-0210
title: frob test package-fallback treats pytest exit 5 (no tests collected) as FAIL
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/app/test_runner.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestRunners::test_pytest_exit_5_no_tests_collected_is_neutral_not_fail
- tests/test_testing.py::TestRunners::test_package_fallback_with_zero_tests_is_ok_end_to_end
- tests/test_testing.py::TestRunners::test_exit_code_is_data
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private: editing a file in a package with no tests (activities/git-heist/) makes frob test --base HEAD~1 report [FAIL] python exit=5. pytest exit 5 = collected 0 tests; the package fallback should degrade to the same neutral nothing-touched-selects-any-test outcome the empty-selection path prints. Regression test: fixture package with a source edit and zero tests -> PASS/neutral, not FAIL.

Scope widened to include `src/frob/app/test_runner.py`: the FAIL/PASS status line is printed there (`_print_outcomes`), so the neutral-outcome fix needs a matching status branch in that file alongside the `is_neutral_outcome` classification in `src/frob/testing/_runners.py`.
---
id: T-0750
title: 'system tests: gitless tmp_path fixture trips COV002/SCOPE001/TODO001 across
  test_cli_check.py'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/system/test_cli_check.py
- tests/system/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
- tests/system/test_cli_check.py::TestCheckGatesStage::test_only_gates_passes_once_bound_and_tested
- tests/system/test_cli_check.py::TestCheckTicketScopedAlwaysReportsOnFailure::test_ticket_scoped_nonzero_exit_has_diagnostic_output
- tests/system/test_cli_check.py::TestCheckStampBaselineAndDelta::test_stamp_baseline_writes_stamp
- tests/system/test_cli_check.py::TestCheckSkipFlags::test_skip_ruff
- tests/system/test_cli_check.py::TestCheckDocAnchorScopedVsUnscoped::test_scoped_docanchor_matches_unscoped
designated_repro_test: null
threat: null
component: null
---
found while working T-0627: a wide swath of tests/system/test_cli_check.py (TestCheckCleanProject, TestCheckSkipFlags, TestCheckGatesStage, TestCheckDocAnchorScopedVsUnscoped, TestFrobTomlCheckDefaults, TestCheckTypescript, TestCheckStampBaselineAndDelta, TestCheckTicketScopedAlwaysReportsOnFailure) fail on this worktree's post-merge main: _make_project's tmp_path fixture never git-inits, and newly-merged gates (COV002, SCOPE001, TODO001) now error loudly on a missing git repo instead of the older gates that degraded quietly -- 'working diff against base=main failed to load ... this is a load failure, not a clean/empty diff, so it is not silently passing'. Pre-existing as of the T-0627 warm-up merge, not caused by T-0627's changes (verified: T-0627's own new tests pass; this same failure set reproduces independent of T-0627's diff). Fix is either: git-init tmp_path in the shared fixture, or add gate exemptions those specific tests already relied on for the older gate set.
---
id: T-4445
title: 'Windows CI: pre-land lint-diff attribution refuses on a shift-only violation
  (successor to T-4403)'
state: queued
kind: bug
origin: agent
created: '2026-09-12'
priority: high
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_land_lint_diff_attribution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Successor to T-4403 (dropped wrong-premise; drop is terminal so this re-files it). Node id: tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse.
CI run 34675057655 Windows leg (head d0fc8ba1e) still fails tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse with SystemExit: 1 from _assert_touched_files_lint_clean_pre_land (_land_cmd.py:4993). The winrun mirror pass that justified the drop does not reproduce the runner (D:\a checkout, Git Bash, runner ruff version) -- the drop was wrong-premise. Next attempt must reproduce the runner's shape: run the test on the mirror from a path with a drive letter and compare the ruff invocation/output the attribution parses.

ACCEPTANCE: (1) root cause named with the runner-shaped reproduction (drive-letter path, Git Bash) measured on the mirror; (2) the test passes on the mirror under that shape; (3) CI Windows leg green on this node id on the next push. Sprint v0.531.0.

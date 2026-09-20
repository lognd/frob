---
id: T-4445
title: 'Windows CI: pre-land lint-diff attribution refuses on a shift-only violation
  (successor to T-4403)'
state: done
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
body_changes:
- mode: append
  reason: BUG002 confirmatory-only at land; win32-only defect, same shape as T-4404/T-4430
  actor: logan
  at: '2026-09-13'
  old_length: 1134
  new_length: 1909
evidence:
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
- tests/test_ticket_land_lint_diff_attribution.py::TestRuffDiagnosticIdentity::test_backslash_and_drive_letter_case_do_not_break_identity
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

frob:waive BUG002 reason="win32-only defect: the pre-land ruff diff attribution compared os.path.relpath strings that differ only by case/separator on the GitHub Windows runner (D:\a checkout), so the merely-shifted violation was misattributed as new and _assert_touched_files_lint_clean_pre_land exited 1 (CI runs 34675057655, 34708801531). check-repro runs the designated tests at the parent commit on this Linux host where relpath is already canonical, so they pass at the parent by construction; measured on the winrun Windows mirror: tests/test_ticket_land_lint_diff_attribution.py 7/7 pass with the fix. The exact D:-vs-C: cross-drive shape could not be forced on the single-drive mirror; the new diagnostic warning names the mismatching identity pair if it recurs."
---
id: T-3397
title: Reduce ARCH103 decision-point count in _land_cmd._assert_touched_files_lint_clean_pre_land
state: done
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: declare no-behavior-change for pure extraction refactor
  actor: logan
  at: '2026-08-29'
  old_length: 414
  new_length: 692
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_lint_error_in_a_touched_file_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_clean_touched_file_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_empty_touched_set_is_a_no_op
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_genuinely_new_violation_still_refuses
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_second_new_violation_sharing_identity_with_pre_existing_one_still_refuses
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_baseline_unmeasurable_falls_back_to_file_scoped_refusal
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ARCH103 fires on _assert_touched_files_lint_clean_pre_land (6 decision points, I/O + string-formatting). A safe fix needs a consolidating split (per T-3311's lesson: moving code around does not reduce the caller's own branch count unless the split owns ALL the branching) rather than a blind extraction, so it is deferred as tracked follow-up work rather than attempted as a drive-by in a mixed-gate cleanup slice.

frob:no-behavior-change reason="pure ARCH103 complexity split -- extracts the existing refusal-message-format-and-sys.exit(1) tail verbatim into _refuse_pre_land_lint, called from the exact same site with the exact same inputs; no refusal condition or message content changed"
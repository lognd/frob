---
id: T-3394
title: Reduce ARCH103 decision-point count in check_runner._apply_tier_a_and_reverify
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
- src/frob/app/check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: declare no-behavior-change for pure extraction refactor
  actor: logan
  at: '2026-08-29'
  old_length: 399
  new_length: 720
evidence:
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_unscoped_fix_refuses_without_fix_all
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_fix_all_still_runs_repo_wide_when_explicitly_requested
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_ticket_scoped_fix_never_touches_files_outside_declared_scope
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ARCH103 fires on _apply_tier_a_and_reverify (7 decision points, I/O + string-formatting). A safe fix needs a consolidating split (per T-3311's lesson: moving code around does not reduce the caller's own branch count unless the split owns ALL the branching) rather than a blind extraction, so it is deferred as tracked follow-up work rather than attempted as a drive-by in a mixed-gate cleanup slice.

frob:no-behavior-change reason="pure ARCH103 complexity split -- extracts the existing sys.exit(1)/_log.error refusal verbatim into _refuse_unscoped_fix_pass with no change to when/how it refuses; test_unscoped_fix_refuses_without_fix_all passing at both main and the fix is expected, not confirmatory-only, per T-1616"
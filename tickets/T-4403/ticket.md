---
id: T-4403
title: 'pre-land lint-diff attribution refuses on Windows: shift-only violation mis-detected
  as new'
state: queued
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: null
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
CI run 34546329688, Windows leg only.

Node id: tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse

Traceback tail (verbatim):
tests\test_ticket_land_lint_diff_attribution.py:167: in test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
    _assert_touched_files_lint_clean_pre_land(
src\frob\app\ticket_runner\_land_cmd.py:4911: in _assert_touched_files_lint_clean_pre_land
    _refuse_pre_land_lint(ticket_id, new_violations, py_files)
src\frob\app\ticket_runner\_land_cmd.py:4941: in _refuse_pre_land_lint
    sys.exit(1)
E   SystemExit: 1

The test asserts a violation that only shifted line numbers (pre-existing,
not new) must NOT trigger a pre-land refusal, but on Windows it does.
Likely mechanism: the shift-detection compares ruff finding identity keyed
partly on file path text, and ruff on Windows emits backslash paths while
the diff/attribution side compares against a POSIX-style path built with
"/", so the same violation on the same file fails to match pre- vs
post-diff and reads as new. Fix production code to normalize paths (e.g.
via PurePosixPath / os.path.normcase-aware comparison, or Path equality
instead of string equality) with a declared reason, rather than adding a
platform skip -- this is real cross-platform lint-diff behavior CI must
exercise on Windows.
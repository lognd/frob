---
id: T-4457
title: 'Windows CI: lint-diff attribution still refuses after T-4445; surface the
  identity mismatch and stop relpath from crossing drive letters'
state: done
kind: bug
origin: agent
created: '2026-09-13'
priority: critical
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
  reason: 'record BUG002 waiver: check-repro confirmatory-only on Linux for the win32-only
    cross-drive defect'
  actor: logan
  at: '2026-09-13'
  old_length: 2556
  new_length: 3429
evidence:
- tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_same_drive_relativizes_normally
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_cross_drive_diag_and_base_do_not_crash
- tests/test_ticket_land_lint_diff_attribution.py::TestRelativizeDiagPath::test_live_and_baseline_pass_agree_across_differently_drived_trees
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34739935923 (head b69c67b1b, INCLUDES T-4445's os.path.normcase fix and its diagnostic warning), Windows leg: tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse still exits 1 from _refuse_pre_land_lint (src/frob/app/ticket_runner/_land_cmd.py:5063). The CI log shows ONLY the trimmed traceback: pytest captured both the refusal message on stderr and T-4445's _log.warning, so the runner never tells us which identity pair failed to match. Two things to do. (A) VISIBILITY, test-only: wrap the call in the test with `try/except SystemExit` (or pytest.raises inside a helper) and re-raise as an AssertionError whose message embeds capsys/caplog output (the refusal text, the T-4445 warning with the live identity and the baseline identity set, the raw ruff JSON `filename` values and the git-diff paths), so the next Windows run prints the mismatch in the E lines. (B) LIKELY CAUSE to fix at the same time: the GitHub runner's checkout lives on D:\a\frob\frob while pytest's tmp_path (the fixture repo) is on C:\Users\runneradmin\AppData\Local\Temp; `os.path.relpath(path, start)` across drive letters raises ValueError ("path is on mount 'C:', start on mount 'D:'") on Windows, and whichever side of the identity computation (live ruff pass vs merge-base baseline snapshot pass, which may run in a different directory) catches that or falls back to an absolute/different-shaped path produces two identities that never compare equal, so every pre-existing violation reads as NEW. The winrun mirror is single-drive, which is why every local measurement passes. Fix: compute both identities relative to the FIXTURE/REPO ROOT being linted (the same root for both passes), never relative to the process cwd; if the baseline pass lints a snapshot in another directory, relativize against THAT snapshot's root; never let relpath cross drives (guard with os.path.splitdrive and fall back to normcase(abspath) consistently on both sides). Add a unit test that feeds a C:-rooted repo path and a D:-rooted cwd through the identity function (pure function, mock-free) and asserts equal identities for the same file across the two passes. ACCEPTANCE: (1) the test's failure message on the runner names the mismatching pair (if it still fails); (2) unit test for the cross-drive shape passes on Linux and the mirror; (3) the node id passes on the next Windows CI run. Sprint v0.531.0 (last Windows test failure besides T-4456). Successor of T-4445/T-4403.



frob:waive BUG002 reason="check-repro on this (Linux) host runs the designated repro test at the parent commit, where the fix is a no-op (os.path.normcase/relpath/splitdrive are all identity operations on POSIX) -- the test PASSED_AT_PARENT here by construction, not by omission. The defect this test guards against is Windows-only (cross-drive path text between a GitHub-hosted runner's D:\\ checkout and its C:\\ process temp dir, CI run 34739935923) and cannot be forced to fail-before/pass-after on Linux. The new TestRelativizeDiagPath unit tests exercise the actual win32 drive-letter shapes directly via ntpath (mock-free, platform-independent of the host running them), and were verified to fail against the pre-fix _ruff_diagnostic_identity shape (a plain os.path.relpath(diag.file, base.resolve()) with no drive guard) before this change, then pass after it."
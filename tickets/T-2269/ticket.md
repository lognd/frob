---
id: T-2269
title: 5 tests in tests/test_coverage.py assert on Makefile recipe text T-2240 already
  retired
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_target_restores_and_verifies_natives_before_pytest
designated_repro_test: tests/test_coverage.py::TestCoverageTargetNativesGuard::test_coverage_target_restores_and_verifies_natives_before_pytest
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-08-16 while working T-2256 (COV003 evidence repointing for
T-2240's Makefile rewrite). T-2240 (dcb07727d8ce) rewrote `coverage:` /
`coverage-fast:`'s Makefile recipe bodies to delegate to `uv run frob
coverage --full` / `uv run frob coverage .`, removing the old inline shell
(subprocess-rc generation, serial-rerun-on-flake, `coverage combine`,
etc.). It correctly rewrote `tests/unit/test_makefile_coverage.py` (924 ->
195 lines) to match, but did NOT update the OTHER file that also asserts
on the live Makefile recipe text: `tests/test_coverage.py`.

5 tests in `tests/test_coverage.py` now fail against the current Makefile
(verified: `uv run pytest tests/test_coverage.py -p no:cacheprovider -q`,
all 5 fail with `ValueError: substring not found` / `AssertionError`,
asserting on text like "pytest --cov", "coverage combine", "-n 0",
"--last-failed", "make core" that no longer appears in `make -n coverage`'s
dry-run output):

- TestCoverageTargetNativesGuard::test_coverage_target_restores_and_verifies_natives_before_pytest
- TestCoverageTargetFlakeTolerance::test_first_pass_failure_does_not_abort_the_recipe
- TestCoverageTargetFlakeTolerance::test_rerun_is_serial_and_scoped_to_last_failed
- TestCoverageTargetFlakeTolerance::test_combine_xml_stamp_run_unconditionally_after_the_rerun
- TestCoverageTargetFlakeTolerance::test_target_exit_reflects_final_status_not_always_zero

Same root cause and same fix shape as T-2240's own `test_makefile_coverage.py`
rewrite: these `TestCoverageTargetFlakeTolerance`/`TestCoverageTargetNativesGuard`
classes assert on retired shell-recipe text (serial-rerun-on-flake,
`coverage combine`, natives-restore-before-pytest ordering) that the new
`frob coverage --full`/`native_coverage_refresh` delegation moved into
Python and (per `tests/test_coverage.py::TestNativeCoverageRefresh` /
`TestSpawnWithWatchdog` / `TestPytestOutcomeWorkerCrashRecovery`) already
covers with real, passing tests -- these 5 are very likely now-redundant
dead weight the same way the 924 deleted lines in
`test_makefile_coverage.py` were, not a fixable assertion-text bug.

OUT OF SCOPE for T-2256 (ledger-only, `tickets/archive` + `tickets.md`):
this is a production test file (`tests/test_coverage.py`), not a ticket
evidence citation. Filing rather than fixing inline.

Do NOT restore the old Makefile shell to make these pass -- same
"do not undo T-2240" constraint T-2256 itself operates under.
## Done report

Changed:
src/frob/gates/_tickets_gate.py::_utc_today
src/frob/gates/_tickets_gate.py::_tick004_queue_rot
src/frob/gates/_tickets_gate.py::_ledgerv1001_violations

Added `_utc_today()` (`datetime.now(timezone.utc).date()`) and swapped both `date.today()` call sites (`_tick004_queue_rot`'s age computation and `_ledgerv1001_violations`'s sunset comparison) to use it, so the same tickets.md content on the same commit computes the same calendar date -- and therefore the same TICK004 WARN/ERROR severity at the 2x-threshold boundary -- regardless of the process's local timezone.

Evidence: tests/test_tickets_priority.py::TestTick004QueueRot::test_severity_is_utc_deterministic_across_local_timezones -- creates a ticket exactly one day past the 2x-threshold ERROR boundary (the measured CI shape: HIGH priority, 15d/threshold-7d), computes `_tick004_queue_rot` under `TZ=Pacific/Kiritimati` (UTC+14) and `TZ=Etc/GMT+12` (UTC-12), and asserts identical severity. Full TestTick004QueueRot class (14 tests) and tests/test_tickets_migration.py (23 tests, covers LEDGERV1001) both pass.

Filed: none (this IS the filed CI-followup ticket).

Gates: ruff-check/ruff-format/ty clean on the touched files. `frob ticket done-report` hung past 590s in this worktree (same pre-existing tool stall seen on T-4391/T-4392, not investigated further under this ticket's scope) so this section was written directly. `--check-repro` could not produce an automated fail-then-pass verdict for the same T-2025 squash-commit reason as the sibling tickets; manually confirmed the new test's assertion would fail (severities differ) against the pre-fix local-clock `date.today()` and passes against the fixed `_utc_today()`.

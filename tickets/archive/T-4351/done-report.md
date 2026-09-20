## Done report

Windows suite's first completed run measured 5 failures (SUITE-RESULT:
exitstatus=1 collected=13786 failed=5), 1 not-mine (test_scaffold_dx,
owned by T-4349). Of the remaining 4, 3 are fixed here with MEASURED
Windows verification via winrun; the 4th could not be reproduced
despite substantial effort and is tracked separately.

1. tests/unit/test_main_entry.py::TestEnsureVenv::test_sets_when_unset
   Root cause: `_ensure_ambient_virtual_env` (T-4308) round-trips
   `sys.prefix` through `Path(...)` before storing it in VIRTUAL_ENV,
   which normalizes separators for the host platform. The test compared
   the result against a hardcoded POSIX literal ("/fake/venv"), so it
   failed on Windows where `str(Path("/fake/venv"))` is `\fake\venv`.
   Fix: compare against the same `str(Path(fake_prefix))` round-trip.
   MEASURED on Windows via winrun: failed before, 3/3 passed after.

2. tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering
   Root cause (traced via extensive winrun repro, see commit body):
   the test shells out to a SECOND, nested `uv run frob agent env ...`
   inside its own bash `eval`. On Windows, when that inner uv's active-
   venv match against the current directory doesn't hold, uv falls back
   to a bare `python3` PATH lookup, which on a stock Windows image hits
   the Microsoft Store execution-alias stub instead of a real
   interpreter -- corrupting the exact stdout the test evals ($()
   captures the stub's own diagnostic text, `eval` then chokes on it).
   Fix: invoke `sys.executable -m frob agent env ...` instead --  an
   absolute path needing no venv resolution or PATH search at all,
   while still exercising the real frob CLI's stdout-purity behavior
   under test. MEASURED on Windows via winrun: 4/4 passed after (could
   not force the ORIGINAL failure to reproduce on this particular
   Windows mirror -- it has WSL installed, which shadows plain "bash"
   resolution differently than a stock GH windows-latest runner -- but
   the fix removes the mechanism regardless and is verified functionally
   correct and equally effective at the test's own stated purpose).

3. tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_tracked_file_edit_forces_process_gate_recompute
   Root cause, MEASURED directly from the CI log: `assert 0.0 != 0.0`.
   The test read `stats.timing_s["archgate"] != 0.0` as proof a real
   recompute happened, but a genuine recompute of this test's one-line
   file can finish inside `time.process_time()`'s own clock granularity
   on Windows and legitimately report 0.0 -- indistinguishable from the
   SAME 0.0 sentinel `_seed_preloaded_process_cache` uses for an actual
   cache HIT. Fix: force the process gate to run serially in the test's
   own process (`FROB_DISABLE_POOL_PRELOAD=1`, T-3670's existing lever)
   and spy directly on `frob.gates.arch_gate`, so the assertion is a
   real call-count fact instead of a clock reading -- correct and
   deterministic on every platform regardless of timer resolution.
   MEASURED on Windows via winrun: 2/2 passed after.

4. tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
   NOT FIXED here. Filed as a new ticket (T-4357) with a
   documented, plausible-but-unconfirmed hypothesis (an asymmetric
   Windows-only spawn-resolution fragility in the same code path
   T-4257 already fixed one instance of). Could not force a
   reproduction on the available Windows mirror across single-run,
   15x/10x serial loops, whole-module and xdist-parallel runs, and both
   `.venv\Scripts\python.exe -m pytest` (no ambient VIRTUAL_ENV) and
   `uv run pytest` (ambient VIRTUAL_ENV active, matching CI's own launch
   shape) invocation styles -- all passed every time. Per the standing
   directive to measure rather than reason, and to re-run before
   believing/dismissing a surprising reading, I am not forcing an
   unverified change to this test; the next completed Windows suite run
   is the cheapest way to learn whether this recurs.

Consequently the advisory (continue-on-error) flag on the windows-latest
leg is NOT proposed for removal in this ticket -- 3 of 4 known failures
are fixed and verified, but the 4th is unconfirmed, so the leg's
overall conclusion still cannot be trusted as a hard gate yet.

### Changed
```
 tests/test_gate_cache.py           | 34 ++++++++++++--
 tests/test_worktree_guard.py       | 16 ++++++-
 tests/unit/test_main_entry.py      | 11 ++++-
 tickets/T-4351/done-report.md      | 87 +++++++++++++++++++++++++++++++++++
 tickets/T-4351/ticket.md           | 33 +++++++++++++-
 tickets/T-4357/ticket.md | 92 ++++++++++++++++++++++++++++++++++++++
 6 files changed, 265 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestEnsureVenv::test_sets_when_unset` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestEnsureVenv::test_leaves_existing` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestEnsureVenv::test_skips_non_venv` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_stdout_contains_only_export_lines` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_diagnostics_still_appear_on_stderr` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_no_fleet_context_still_produces_valid_eval_output` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_tracked_file_edit_forces_process_gate_recompute` (pytest node id, verified passing when recorded)
- `tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_second_warm_run_serves_process_gate_from_cache` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 4731 warning(s), 956 waived
- error-findings: none (measured, zero errors)

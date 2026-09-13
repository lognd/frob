## Done report

Windows CI runner clock: the land phase elapsed prefix used time.monotonic, whose win32 tick granularity is ~15.6ms, so two phase lines 50ms apart both formatted as [+0.0s] and tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines asserted 0.0 > 0.0 (CI run 34675057655, Windows leg). Fix: _land_phase_elapsed_seconds in src/frob/app/ticket_runner/_land_cmd.py now uses time.perf_counter (sub-millisecond on win32) and the test sleeps 0.25s between phases so the one-decimal prefix must advance on any supported clock. Measured: 3/3 tests pass on Linux and on the winrun Windows mirror (implementer measurement, 2026-09-12). Evidence: the three node ids in tests/unit/test_land_phase_elapsed_logging.py bound via frob:tests T-4442. The original Done report commit was lost when the post-land rapid sweep removed this worktree (T-4448); rewritten by the coordinator from the implementer's report.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py       | 17 ++++++++++++-----
 tests/unit/test_land_phase_elapsed_logging.py | 13 +++++++++++--
 tickets/T-4442/ticket.md                      |  6 +++++-
 3 files changed, 28 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_seconds_is_monotonic_across_phase_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_non_phase_log_lines_are_left_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_phase_elapsed_logging.py::TestLandPhaseElapsedLogging::test_elapsed_helper_starts_at_zero_on_first_call` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 4812 warning(s), 961 waived
- error-findings: PRE001@tickets/T-4442, TICK004@tickets.md

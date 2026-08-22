## Done report

Built scripts/wait_for_land_slot.py, the shared "wait until a land slot is
free" primitive, alongside fleet_status.py/check_summary.py/verify_lands.py
under scripts/, documented in docs/guides/coordinator-scripts.md.

Design: probe_lands_in_flight(command) shells out to fleet_status.py
(default) or --fleet-status-cmd (override), and is the ONLY place that
parses the "LANDS IN FLIGHT: N" line -- reusing fleet_status.py's own
definition of "a land is in flight" rather than re-deriving it, per the
ticket's explicit requirement. A nonzero exit, a hung probe past
PROBE_TIMEOUT_S, or unparseable output all read as None (UNMEASURED),
never 0.

wait_for_slot(command, max_in_flight, timeout_s, poll_interval_s, on_tick,
sleep, now) is the polling state machine: tracks ever_measured across the
whole call so a timeout after at least one real reading exits EXIT_TIMEOUT
(1), while a run that NEVER got a readable measurement exits
EXIT_MEASUREMENT_FAILED (2) -- checked every iteration, so a probe that
measures once and then starts failing still correctly reports TIMEOUT, not
MEASUREMENT_FAILED. A free slot returns EXIT_SLOT_FREE (0) immediately,
with no fixed sleep imposed on the common uncontended case (verified: zero
time elapses when the first probe already clears).

CLI (main): quiet by default -- exactly one summary line to stdout;
--verbose adds one line per tick to STDERR only (never stdout), so a
caller scripting against exit code + stdout never has to filter tick
noise. --timeout defaults to 480s, below this repo's own 500s/540s
wrapper convention (the exact inconsistency named in the ticket). --max-
in-flight defaults to 0 (the ticket's literal "no land in flight" text);
pass 1 to match the fleet's separate "fewer than 2 is fine to land
against" convention used elsewhere in this session.

POSITIVE CONTROLS, BOTH DIRECTIONS (all as real, running tests, not
narrative):
- test_land_in_flight_then_free_blocks_then_returns: with a land
  genuinely in flight the script blocks (does not return 0 early) until
  it clears.
- test_slot_already_free_returns_immediately: the common case returns 0
  promptly with zero elapsed time -- no fixed sleep.
- test_always_unmeasurable_never_returns_zero: THE control the ticket
  names as the one that proves the point -- the status probe is forced to
  fail (via a monkeypatched probe_lands_in_flight always returning None)
  on every single poll; asserts exit code == EXIT_MEASUREMENT_FAILED and
  != EXIT_SLOT_FREE. Also proved end-to-end through the real CLI with
  nothing stubbed (test_end_to_end_forced_probe_failure_via_fleet_status_cmd,
  `--fleet-status-cmd false`) and manually against the live fleet
  (`--fleet-status-cmd false` -> exit 2, `measurement failed: ...`, never
  0).
- test_always_in_flight_times_out: a fleet genuinely measured in-flight
  the whole window times out with EXIT_TIMEOUT, distinct from both above.
- test_measured_then_unmeasurable_is_timeout_not_measurement_failure:
  once any real reading was obtained, later probe failures must not
  retroactively downgrade a genuine (if incomplete) measurement into
  MEASUREMENT_FAILED.

Also manually re-verified against the live fleet: `--timeout 20
--poll-interval 3 --verbose` returned EXIT_SLOT_FREE promptly with the
real "LANDS IN FLIGHT=0" reading.

Filed T-2778 (out-of-scope discovery, not fixed here): WIRE001's
call-graph walk cannot resolve a symbol wired only as a passed-by-name
callback argument (_print_tick is a genuine, exercised production
callback but reads as unwired) -- T-1592's existing permanent="true"
escape hatch is deliberately restricted to tests/ private helpers, so
this is disclosed via frob:waive WIRE001 follow_up="T-2778"
(renumbers to a real id at land, T-1125) rather than forced through that
narrower hatch.

Scope extended (frob ticket scope --add) to include
tests/unit/test_coordinator_scripts.py, since the ticket's own brief
requires positive-control unit tests alongside the script and doc.

### Changed
```
 docs/guides/coordinator-scripts.md     |  97 +++++++++-
 scripts/wait_for_land_slot.py          | 343 +++++++++++++++++++++++++++++++++
 tests/unit/test_coordinator_scripts.py | 274 ++++++++++++++++++++++++++
 tickets/T-2775/ticket.md               |  25 ++-
 tickets/T-2778/ticket.md     |  30 +++
 5 files changed, 766 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight::test_reads_a_genuine_count` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight::test_zero_is_a_real_reading_not_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight::test_nonzero_exit_is_unmeasured` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight::test_unparseable_output_is_unmeasured` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight::test_probe_timeout_is_unmeasured` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight::test_probe_oserror_is_unmeasured` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWaitForSlot::test_slot_already_free_returns_immediately` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWaitForSlot::test_land_in_flight_then_free_blocks_then_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWaitForSlot::test_always_in_flight_times_out` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWaitForSlot::test_always_unmeasurable_never_returns_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWaitForSlot::test_measured_then_unmeasurable_is_timeout_not_measurement_failure` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWaitForSlot::test_verbose_tick_hook_receives_every_reading` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWaitForLandSlotMain::test_quiet_by_default_prints_one_summary_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWaitForLandSlotMain::test_verbose_adds_per_tick_lines_to_stderr` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestWaitForLandSlotMain::test_end_to_end_forced_probe_failure_via_fleet_status_cmd` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: 18 error(s), 921 warning(s), 709 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md

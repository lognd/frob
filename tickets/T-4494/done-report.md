## Done report

Two independent fixes, both near-zero-cost until triggered, matching the
T-4408 measured incident (21 minutes at 109% CPU in the land process
itself, no further log line, py-spy needing root on this box, kill
-USR1 killing the land with exit 138 because no handler was ever
installed outside frob serve's daemon).

1. Unconditional handler install
   frob.testing._stackdump.install_stackdump_handler gained a
   keyword-only force: bool = False parameter. force=True bypasses
   STACKDUMP_ENV entirely. _land (src/frob/app/ticket_runner/_land_cmd.py)
   calls install_stackdump_handler(force=True) at its own very top --
   before _apply_land_default_queue/_dispatch_land_mode, so even a fast
   --plan/--queue/--status/--drain call has the handler installed for
   the life of that process.

   Extracted the actual dump-writing body out of dump_all_thread_stacks
   into a new write_stack_dump(header: str) -> Path helper (no
   duplication between the SIGUSR1 handler and the new watchdog, which
   also needs to trigger the identical dump without a signal handler's
   (signum, frame) call shape).

2. Silent-phase self-dump watchdog
   _land_last_phase_log_at (new module global) is written by the
   existing _LandPhaseElapsedFilter every time it prefixes a "ticket
   land: ..." phase line. _start_land_silent_phase_watchdog starts a
   daemon thread right before _land_core (not before -- an early
   --finish/--retire-on-proof return above it is fast and never silent)
   that polls every 5s (_LAND_SILENT_PHASE_WATCHDOG_POLL_S) via
   _land_silent_phase_watchdog and self-dumps (write_stack_dump,
   WARNING-logging the file) the moment no phase line has fired for
   _land_silent_phase_dump_threshold_s's threshold -- [tool.frob]
   land_silent_phase_dump_s in pyproject.toml, read directly via
   tomllib (config.py is not in this ticket's scope, so no new
   AppConfig field), defaulting to 600.0 (10 minutes) when
   absent/unparsable. Dumps at most once per silence EPISODE (a fresh
   phase line resets the "already dumped" flag), so a land that
   recovers and later goes silent again dumps again. _land's finally
   stops the thread (stop_event.set()) the instant _land_core returns.

   BUG CAUGHT BY THE TEST SUITE ITSELF: the watchdog's own WARNING
   message originally started with "ticket land:" (the same literal
   prefix _LandPhaseElapsedFilter matches on) -- since both share the
   same logger, the watchdog's own self-dump log line was being read
   back by the filter as a fresh phase line, resetting its own
   "dumped_this_episode" flag and dumping again every threshold period
   forever instead of once. Caught by
   TestSilentPhaseWatchdog.test_fires_once_after_threshold_then_waits_for_next_episode
   (observed 3 dumps instead of 1); fixed by rewording the WARNING
   message to not start with the phase-line prefix, with a comment at
   the call site explaining the trap for the next person touching this.

Doc: added "## Silent-phase self-dump watchdog (T-4494)" to
docs/modules/tickets-landing.md, right after the existing "Phase-
transition elapsed-seconds logging (T-4417)" section it builds on.
docs/modules/tickets-landing.md was added to this ticket's scope
(frob ticket scope --add, reason recorded) since AFFECT001/COV001
require a doc anchor for the new public/changed symbols and this is
where every other _land_cmd.py T-#### land feature already documents.
NOTE: the scope-add's mirror to the shared root kept refusing with
LandInProgress across several retries (other tickets' lands were
running the whole session) and I could not confirm it landed on the
shared root's own view before finishing -- the worktree's own
tickets/T-4494/ticket.md (which is what actually lands) has the
correct 4-file scope; `frob ticket show T-4494` run from the root still
shows the original 3-file scope as of this report.

BUG002 repro: split the change into two commits so a real pre-fix ref
exists in THIS worktree's own history (the T-2025 "already-landed
tickets squash test+fix into one commit" limitation doesn't apply
before land) --
  c2c6b0131 test(land): add T-4494 SIGUSR1/watchdog repro tests (fail against unfixed code)
  f237fdba4 feat(land): install SIGUSR1 stack-dump handler and silent-phase watchdog (T-4494)
designated tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1::test_survives_with_a_dump_after_the_fix
as the repro against --base-ref c2c6b0131: confirmed FAILED_AT_PARENT
(install_stackdump_handler(force=True) raises TypeError at that commit
-- the force kwarg does not exist yet), then --check-repro against the
same base-ref reconfirmed FAILED_AT_PARENT.

Exec-via-list subprocess test (mirrors tests/system/test_ci_hang_guard_positive_control.py's
_run_under_watcher shape): _spawn_and_signal launches a land-like
sys.executable -c subprocess, sends it a real SIGUSR1, and observes:
  - without any handler installed: Popen.returncode == -signal.SIGUSR1
    (the same underlying condition a shell reports as exit 138)
  - with install_stackdump_handler(force=True) installed: the process
    survives, prints "survived", exits 0, and leaves a dump file behind

ruff check/format: 0 errors on touched files (one pre-existing
ruff-format warning, tests/test_tickets_triage_dates.py, untouched by
this ticket).

Serial pytest (-p no:xdist), all passing:
  tests/unit/test_land_stackdump.py            10 passed
  tests/unit/test_stackdump.py                  (existing, unaffected)
  tests/unit/test_conftest_stackdump.py         (existing, unaffected)
  tests/unit/test_land_phase_elapsed_logging.py (existing, unaffected)
  tests/unit/test_land_default_queue.py         (existing, unaffected)
  tests/ticket_land_suite/test_land_core.py     51 passed (existing, unaffected)

Evidence bound (--base-ref dev), 6 node ids across the ticket's 2
acceptance criteria:
  [1] SIGUSR1 -> every thread's stack dumped, land continues:
      TestLandLikeSubprocessSigusr1.test_survives_with_a_dump_after_the_fix
      TestLandLikeSubprocessSigusr1.test_dies_without_the_handler
      TestInstallStackdumpHandlerForce.test_force_installs_regardless_of_env
  [2] silent phase past threshold -> self-dump at WARNING:
      TestSilentPhaseWatchdog.test_fires_once_after_threshold_then_waits_for_next_episode
      TestSilentPhaseWatchdog.test_never_fires_while_phase_lines_keep_arriving
      TestSilentPhaseDumpThreshold.test_reads_configured_value

Worktree git status --short: empty. Root /home/logan/projects/frob
git status --short: empty (the scope-mirror lag noted above is a
ledger-visibility gap, not a dirty working tree).

### Changed
```
 design/frob.strata                                 |   6 +-
 .../registry/capability-via-ratchet.lock.json      |  18 +-
 docs/modules/tickets-landing.md                    |  49 ++++
 src/frob/app/ticket_runner/_land_cmd.py            | 155 +++++++++-
 src/frob/testing/_stackdump.py                     |  68 +++--
 tests/unit/test_land_stackdump.py                  | 321 +++++++++++++++++++++
 tickets/T-4494/ticket.md                           |  42 ++-
 7 files changed, 621 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1::test_survives_with_a_dump_after_the_fix` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stackdump.py::TestLandLikeSubprocessSigusr1::test_dies_without_the_handler` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stackdump.py::TestInstallStackdumpHandlerForce::test_force_installs_regardless_of_env` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stackdump.py::TestSilentPhaseWatchdog::test_fires_once_after_threshold_then_waits_for_next_episode` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stackdump.py::TestSilentPhaseWatchdog::test_never_fires_while_phase_lines_keep_arriving` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_stackdump.py::TestSilentPhaseDumpThreshold::test_reads_configured_value` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

## Done report

Changed:
- src/frob/process/_pid_liveness.py (new): pid_alive, pid_alive_tristate,
  _pid_alive_windows, module-level _kernel32 backend resolution
- src/frob/mutate/_journal.py: _pid_alive/_pid_alive_windows removed,
  now imports pid_alive directly from the shared module
- src/frob/tickets/_land.py: _probe_land_lock_pid_liveness delegates to
  pid_alive_tristate instead of its own os.kill(pid, 0) probe
- docs/modules/process.md: new "PID liveness (T-3018)" section
- tests/unit/test_process_pid_liveness.py (new): POSIX + faked-Windows
  coverage for both pid_alive and pid_alive_tristate
- tests/test_ticket_land.py: TestProbeLandLockPidLivenessDelegatesToSharedModule
  proves _land.py's own function genuinely delegates (faked Windows
  backend), not just coincidentally matches behavior

Call sites touched: 2 (src/frob/tickets/_land.py's
_probe_land_lock_pid_liveness -- the ticket's own finding -- and
src/frob/mutate/_journal.py's _pid_alive, T-3003's already-safe copy,
now pointed at the same shared implementation instead of carrying its
own). src/frob/tickets/_leases.py (also in this ticket's declared scope)
was checked and carries NO os.kill liveness probe at all -- grepped the
whole repo for `os.kill(` and confirmed only frob.process._reap.py's
self-signaling/SIGTERM calls (unrelated: real kills, not liveness
probes, os.getpid()-targeted) remain outside the new shared module. No
change was needed there; the ticket's "reportedly carries it too" hedge
did not pan out on inspection.

Extraction: YES, to frob.process._pid_liveness -- pid_alive (bool) for
_journal.py's original 2-state need, pid_alive_tristate (bool | None)
preserving _land.py's stricter confirmed-dead/ambiguous/alive contract
(only a CONFIRMED-dead land-lock holder may ever be auto-reclaimed).
Both consumers import the function by its BARE name (frob.gates._wire's
WIRE001 reach-scan deliberately excludes a dot-qualified call as
untrustworthy evidence for a plain FUNCTION record -- a real, intentional
gate design this ticket had to work with, not a bug).

Windows verification: a fake `kernel32` (OpenProcess/GetExitCodeProcess/
CloseHandle) monkeypatched onto _pid_liveness._kernel32, mirroring
frob.process._lock's own T-2934 precedent for faking msvcrt on Linux CI.
Confirmed: (1) an alive-per-the-fake pid reports True, (2) an exited pid
reports False, (3) an OpenProcess failure (unknown pid) reports False,
(4) the access mask requested is ALWAYS PROCESS_QUERY_LIMITED_INFORMATION,
never a kill-capable mask, and (5) pid_alive_tristate never returns
ambiguous (None) on the Windows backend -- it is definitive by
construction. Windows CI itself was not run (cannot be triggered from
this environment); the fake exercises the exact code path a real
Windows process would take.

Evidence: 13 node ids bound above.
Filed: none (no out-of-scope findings this ticket needed to defer).
Gates: frob check --ticket T-3018 --only wire/ruff clean for every file
this ticket touches (WIRE001 waived once, justified above); remaining
gate-summary noise (DRIFT002 on unrelated pre-existing files, ruff
E501/format on src/frob/narrative/_cli.py and ~50 other files) is
repo-wide and untouched by this diff.

### Changed
```
 docs/modules/process.md                 |  27 +++++
 src/frob/mutate/_journal.py             |  84 ++++------------
 src/frob/process/_pid_liveness.py       | 146 +++++++++++++++++++++++++++
 src/frob/tickets/_land.py               |  46 +++++----
 tests/test_ticket_land.py               |  58 +++++++++++
 tests/unit/test_process_pid_liveness.py | 170 ++++++++++++++++++++++++++++++++
 tickets/T-3018/ticket.md                |  53 +++++++++-
 7 files changed, 499 insertions(+), 85 deletions(-)
```

### Evidence
- `tests/unit/test_process_pid_liveness.py::TestPidAlivePosix::test_current_process_is_alive` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAlivePosix::test_process_lookup_error_is_dead` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAlivePosix::test_permission_error_is_conservatively_alive` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAliveTristatePosix::test_process_lookup_error_is_confirmed_dead` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAliveTristatePosix::test_permission_error_is_ambiguous_not_alive` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAliveTristatePosix::test_live_pid_is_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend::test_alive_pid_reports_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend::test_exited_pid_reports_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend::test_unknown_pid_open_process_fails_reports_false` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend::test_never_requests_kill_capable_access_rights` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_pid_liveness.py::TestPidAliveWindowsBackend::test_tristate_never_returns_ambiguous_on_windows_backend` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestProbeLandLockPidLivenessDelegatesToSharedModule::test_windows_backend_alive_pid_is_true` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestProbeLandLockPidLivenessDelegatesToSharedModule::test_windows_backend_never_ambiguous` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 60 error(s), 1305 warning(s), 856 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/entity_architecture.md, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC006@tickets/T-3015/ticket.md, DOC006@tickets/T-3022/ticket.md, DOC006@tickets/T-3023/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, E501@/home/logan/projects/frob/.claude/worktrees/t3018-series/src/frob/narrative/_cli.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-3018, REF001@docs/strata/entity_architecture.md, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@tests/unit/strata/entity_arch/storage_cheap.strata, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py

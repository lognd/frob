## Done report

Changed:
- src/frob/process/_reap.py (new): reap_active_multiprocessing_children,
  install_sigterm_reaper, _sigterm_handler, reap_orphaned_forkservers,
  _is_orphaned_forkserver, _process_start_age_s, DEFAULT_ORPHAN_AGE_FLOOR_S
- src/frob/process/__init__.py: export the four public _reap symbols above
- src/frob/__main__.py: main() calls install_sigterm_reaper() before
  dispatch; _dispatch calls _reap_orphaned_forkservers_best_effort() for
  the `check` subcommand (frob:waive ARCH001 follow_up=T-2452 --
  _dispatch was already over the 60-line threshold on main before this
  ticket touched it; splitting the whole argv-routing table is a real
  refactor filed as a follow-up, out of scope here)
- scripts/fleet_status.py: orphaned_forkserver_count, wired into
  _land_status_lines/_print_land_status (new ORPHANED FORKSERVERS line)
- docs/modules/process.md: new "Forkserver reaping (T-2443)" section
- docs/modules/app.md: Entry point section updated for the new
  install_sigterm_reaper call
- docs/guides/coordinator-scripts.md: new orphaned_forkserver_count
  anchor/section; _land_status_lines/_print_land_status sections updated;
  also fixed a pre-existing DOC011 stale-draft-id citation at line ~807
  ("(T-draft-354a6b64)") unrelated to this ticket's own work but living
  in a file this ticket already touches -- confirmed via `git log -S`
  that it predates this ticket, trivial one-line prose fix, not filed as
  a separate ticket
- tests/unit/test_process_reap.py (new, 15 tests)
- tests/unit/test_main_entry.py: TestMainInstallsSigtermReaper (1 test)
- tests/unit/test_coordinator_scripts.py: TestOrphanedForkserverCount (4
  tests) + 2 tests on TestPrintLandStatus

Root cause (confirmed by reading the code, not just process-table
inference): `frob.gates._run_combined_jobs` already shuts its
ProcessPoolExecutor down correctly on every normal/exception path
(`try/finally: ppool.shutdown(wait=True)`, pre-existing and correct). The
leak is that Python's DEFAULT SIGTERM disposition terminates the
interpreter immediately with NO exception raised and NO `finally` block
run -- this fleet's routine `timeout 540 uv run frob check ...` wrapper
sends exactly that signal, and `frob.__main__` had no SIGTERM handler at
all (verified: the only `signal.signal` call anywhere in src/frob was
tests/_stackdump.py's unrelated SIGUSR1 hook). The worker processes
`ProcessPoolExecutor` spawned therefore survive the kill untouched, and
because each worker holds its own duplicate of the forkserver helper's
"alive" pipe write-end (stdlib `multiprocessing.forkserver.ForkServer.
connect_to_new_process` hands `self._forkserver_alive_fd` to every child
it creates -- verified by reading CPython's own
`multiprocessing/forkserver.py`), the helper's EOF-triggered self-
shutdown only fires once EVERY holder of that fd has exited -- one
orphaned worker keeps the forkserver helper alive too.

Fix does not touch `frob.gates` pool construction/sizing/shutdown at all
-- and could not have during most of this session (T-2430 held a live
cross-worktree lease on src/frob/gates/__init__.py):
1. install_sigterm_reaper (called from frob.__main__.main, first thing,
   before any dispatch) installs a SIGTERM handler that reaps
   multiprocessing.active_children() -- process-wide stdlib state,
   covers a ProcessPoolExecutor's workers regardless of which module
   constructed the pool -- then chains to the platform default so exit
   behavior (128+15) is unchanged for callers.
2. reap_orphaned_forkservers (best-effort, called from _dispatch only
   for the `check` subcommand) is the defensive half: a /proc sweep for
   forkserver helpers already reparented to init and older than 300s,
   SIGTERM'd proactively.

Positive controls (both run manually against a real fleet-contended
machine):
- MUST-NOW-CLEAN: `frob check --only gates-native` backgrounded, SIGTERM'd
  8s in once the process pool had spawned a forkserver (pid 389248) with
  4 live workers. Log: "process: SIGTERM received -- reaping
  multiprocessing children" / "process: reaping 4 lingering
  multiprocessing child(ren): [...]". Re-scanned the whole process table
  3s after kill (exit_status=143): neither the forkserver nor any of its
  4 workers exist anymore, under ANY ppid.
- MUST-STILL-PASS: `frob check --only gates-native --json` run to normal
  completion twice (16.5s wall each). Per-gate finding counts identical
  across both runs: gate:ARCH 70, gate:DRIFT 17, gate:EXHAUST 332,
  gate:LARGE 78, gate:PERF 175. No change to pool sizing/mp_context, so
  parallelism is unchanged by construction, not just by measurement.

fleet_status.py acceptance [2]: orphaned_forkserver_count now prints
"ORPHANED FORKSERVERS: N ..." in _print_land_status's existing report,
next to the swap-pressure guidance line it exists to make actionable.

Verification: `uv run pytest tests/unit/test_process_reap.py
tests/unit/test_main_entry.py tests/unit/test_coordinator_scripts.py`
161/161 passed (re-verified after every fix round). `uv run frob check
--budget 500 --ticket T-2443` -- ZERO errors on any file this ticket
touched (measured via JSON diagnostic file-path filtering across five
iterations, fixing a real ty type-narrowing bug, a real WIRE001 gap with
a follow_up anchor ticket, a real ARCH001 pre-existing-threshold finding
with a follow_up ticket, and a real pre-existing DOC011 stale-id
citation, each time re-measuring rather than assuming clean).
`--land-parity` timed out at 360s under this session's fleet contention
(multiple concurrent agents/lands) -- disclosed as unmeasured, not
claimed clean; the scoped --budget/--ticket run above plus the two
manual process-table controls are what this Done report stands on.

Filed:
- T-2452 (bug): _dispatch already over ARCH001's 60-line
  threshold on main before this ticket touched it; cited as this
  ticket's own ARCH001 waiver follow_up.
- T-2451 (docs, permanent WIRE001 follow_up anchor, same shape
  as T-1831's precedent): _sigterm_handler is genuinely wired via
  signal.signal, which the callgraph cannot trace as a caller.

Gates: `frob check --budget 500 --ticket T-2443` -- 0 errors on every
file this ticket changed. `static` stage group deferred by budget on
some iterations (not run that invocation, not claimed clean).
`--land-parity` timed out under fleet contention -- disclosed above.

### Changed
```
 tickets/T-2443/done-report.md      | 142 +++++++++++++++++++++++++++++++++++++
 tickets/T-2443/ticket.md           |  46 ++++++++++--
 tickets/T-2451/ticket.md |  38 ++++++++++
 tickets/T-2452/ticket.md |  33 +++++++++
 4 files changed, 255 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_process_reap.py::TestReapActiveChildren::test_terminates_and_joins_active_children` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapActiveChildren::test_escalates_to_kill_if_terminate_does_not_stick` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapActiveChildren::test_no_children_is_a_silent_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestInstallSigtermReaper::test_installs_handler_once` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestInstallSigtermReaper::test_second_call_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_terminates_old_orphaned_forkservers` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_leaves_young_orphaned_forkservers_alone` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainInstallsSigtermReaper::test_main_installs_the_reaper_before_dispatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestIsOrphanedForkserver::test_matches_forkserver_reparented_to_init` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestIsOrphanedForkserver::test_forkserver_with_live_parent_is_not_orphaned` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_reap.py::TestIsOrphanedForkserver::test_non_forkserver_process_is_never_matched` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_counts_forkserver_reparented_to_init` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_ignores_forkserver_with_live_parent` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_ignores_non_forkserver_processes` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCount::test_missing_proc_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_orphaned_forkserver_count_printed_alongside_swap_guidance` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintLandStatus::test_zero_orphaned_forkservers_prints_zero_not_omitted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2443/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2443/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2443/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2443, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md

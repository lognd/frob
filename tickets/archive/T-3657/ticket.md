---
id: T-3657
title: 'win32 round 15: SIGINT persists under CREATE_NO_WINDOW; discriminate in-process
  vs child sender'
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- src/frob/process/_guard.py
- src/frob/check/**
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_no_op_on_non_win32
- tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_no_op_when_env_unset
- tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_installs_and_removes_handler_when_requested
- tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_handler_swallows_ctrl_c_and_ctrl_break
- tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_handler_passes_through_other_events
- tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_exists_and_runs_on_windows
- tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_has_a_bounded_timeout
- tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_sets_frob_disable_exec_before_main
- tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_reuses_the_same_fixture
- tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_pins_project_to_checkout
- tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_precedes_the_windows_test_step
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33521416410 diag (frob at 3291924fc, T-3651 applied):

  diag.out: diag-python-alive -> about to call main() ->
    T-3648-SIGNAL: received SIGINT (signum=2) at frame=threading.py:355 wait
    -> main() raised SystemExit(130)   (elapsed 1.28s, exit 130)
  diag.err: FROB_WIN32_SPAWN_DEBUG shows ALL guarded spawns carry
    creationflags=134218240 (CREATE_NO_WINDOW 0x08000000 +
    CREATE_NEW_PROCESS_GROUP 0x200):
      git rev-parse --abbrev-ref HEAD
      git rev-parse --git-common-dir
      ruff check --output-format json .
      ruff format --check .
    then the SIGINT traceback (main thread in executor.submit ->
    t.start() -> _started.wait(), check/__init__.py:1187), then two
    post-interrupt git spawns, then "frob: interrupted".

CONCLUSION: T-3651 is correctly applied and INSUFFICIENT. A child with
CREATE_NO_WINDOW gets its own hidden console, so the four guarded tool
children cannot be signalling our console -- the round-14 hypothesis is
FALSIFIED (this ticket supersedes that hypothesis). The sender is
something else. ALSO this run's Windows Test step: the suite ran
essentially to completion (collected=13126, testsfailed=20, session
exitstatus=OK) and THEN died by KeyboardInterrupt during session
teardown (threading.py:1169 join) -- same signal class, now at teardown
instead of mid-run (progress: the 20-failure denominator is real, all
in tests/gates_suite).

Round 15 = DISCRIMINATE in-process vs child senders, then fix:
1. Audit UNGUARDED spawn sites in the early check path: anything using
   subprocess directly (not guarded_subprocess_run), os.system,
   multiprocessing, natives probes, uv shims. `git grep -n "subprocess\."
   src/frob | grep -v _guard` and walk the check startup. The check
   task runner itself is a ThreadPoolExecutor (threads, not processes)
   -- so look at what each gate task spawns besides the four above.
2. Extend the diag into a 2-variant matrix in the same step (cheap,
   sequential): (a) current frob check as-is; (b) frob check with
   external tools UNREACHABLE (prepend an empty dir PATH override or
   FROB-native flag that skips tool gates if one exists) so ZERO
   children are spawned. If (b) still gets SIGINT -> in-process sender
   (audit signal.raise_signal / _thread.interrupt_main / SIGBREAK
   handler mapping from T-3565, and any SetConsoleCtrlHandler use);
   if (b) is clean -> a specific child is the sender; bisect by
   re-enabling git-only vs ruff-only.
3. Candidate hard fix once named (keep evidence-driven): if the sender
   is external/unfixable (e.g. a runner-level event), scope a win32
   mitigation INSIDE frob check's non-interactive path: install a
   SetConsoleCtrlHandler/SIG_IGN window around the pipeline guarded by
   an env opt-in (FROB_WIN32_IGNORE_CONSOLE_CTRL=1) set by the CI
   workflow only -- never default, real Ctrl-C must keep working for
   users. Document loudly.
4. Keep FROB_WIN32_SPAWN_DEBUG + the T-3648 signal logger + the diag
   step until a run shows diag exit 0 (or genuine gate result) AND an
   uninterrupted Windows Test step.

Supersedes the falsified round-14 hypothesis of T-3651 (tool-child
sender). Related: T-3648 (signal logger), T-3589 (win32 CI investigation
lineage).

Scope: .github/workflows/ci.yml + src/frob/process/_guard.py +
src/frob/check/** (read-mostly; fix where the evidence points) +
tests/test_ci_workflow_matrix.py if the diag shape changes.
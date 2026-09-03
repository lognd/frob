## Done report

Investigation finding (the ticket's primary deliverable): CI run 33680767948's FROB_CHECK_TIMING
breadcrumbs show every pipeline mark (entry/console-scope/admission/lock/all
*-teardown-enter+exit) firing at ~1.0s, then a ~120s gap before the atexit
breadcrumb fires -- confirming the delay is entirely in Python interpreter
shutdown, not the check pipeline. Investigated frob.gates._open_process_pool
(T-3692's own hypothesis) directly: run_gates's try/finally already calls
ppool.shutdown(wait=True) unconditionally, and the teardown-exit marks (which
fire AFTER run_gates/_run_tasks_concurrently return) land at ~1s in the SAME
breadcrumb set -- proving the pool's own shutdown is fast and NOT the win32
blocker. Added TestProcessPoolGates::test_run_gates_leaves_no_live_pool_
threads_or_children_behind as a real (Linux-runnable) regression test for
this property: it passed even before this ticket's cancel_futures=True
change, confirming the finding rather than reproducing a bug -- hence the
BUG002 waiver above.

Real suspect (out of this ticket's declared scope, filed as T-3708 with
scope src/frob/lang/__init__.py,src/frob/vet/_scan.py): both
_run_parse_with_timeout and _run_with_timeout deliberately abandon a
ThreadPoolExecutor(max_workers=1) worker via shutdown(wait=False) when a
call exceeds its budget. concurrent.futures.thread keeps a process-global
weak registry of every worker thread any ThreadPoolExecutor has ever
spawned, and its own atexit-registered _python_exit() unconditionally
joins ALL of them at interpreter shutdown -- including ones the caller
believed it had abandoned. A genuinely-still-blocked abandoned worker
there matches this bug's signature (fast pipeline return, slow
atexit-to-process-exit gap) far better than the process pool does.

Part B: added FROB_TEST_TOTAL_BUDGET_SECONDS_ENV, a wall-clock-only
watchdog trigger sharing the existing mid-run watchdog thread
(_run_midrun_watchdog extended to accept an optional total_budget_s
alongside its existing optional threshold_s) -- fires independent of
whether any test is still making progress, closing the "slow-but-
continuous-progress" gap AM's T-3692 finding named. Wired into
ci.yml's Windows Test step at 1200s (under its 1500s step budget).
Checked ci.yml's own Windows step `${budget}` interpolation (the
literal bug this ticket's brief named): already fixed by T-3692
(every occurrence uses the curly-brace form); no remaining bare
`$budget` on the Windows step -- the one remaining bare `$budget`
in the file is the (out-of-scope, bash, correctly-quoted) macOS step.

Filed: T-3708 (abandoned timeout worker threads block interpreter
shutdown, win32 122s) -- scope src/frob/lang/__init__.py,
src/frob/vet/_scan.py, referencing this ticket's own narrowing evidence.

Evidence: tests/gates_suite/test_run.py::TestProcessPoolGates::
test_run_gates_leaves_no_live_pool_threads_or_children_behind (designated
repro, force-designated per the BUG002 waiver above);
tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetExceeded::
test_true_at_exactly_the_budget;
tests/unit/test_conftest_midrun_watchdog.py::TestRunMidrunWatchdogTotalBudget::
test_fires_total_budget_exit_with_no_stall_threshold_armed;
tests/unit/test_conftest_midrun_watchdog.py::TestAnnounceTotalBudgetExceededAndHardExit::
test_hard_exits_with_status_1_and_prints_the_inventory_line.
`frob test --base main` passed (exit=0, 70 python test(s), 95.87s).

Gates: `frob check --ticket T-3707` clean except pre-existing repo-wide
findings unrelated to this diff (WAIVE011 ratchet-lock-abandoned, DRIFT/
DUP/TICK/LANG/COV/SCOPE001-on-pre-existing-files -- all explicitly called
out by the tool's own scope-note as REPO-WIDE, not ticket-scoped). ty/
ruff-format clean on every touched file after `frob format`.

Acceptance criteria (win32 CI): unconfirmable from this WSL/Linux host by
construction -- the next Windows CI run's FROB-CHECK-TIMING breadcrumbs
should still show the pipeline completing in ~1s (unchanged, this ticket
did not touch that path) and, if T-3708 lands first, the atexit mark
landing within a second or two of it instead of +120s; if T-3708 has not
yet landed, expect the same ~120s gap to persist, now with this ticket's
own narrowing evidence pointing at the right file.

### Changed
```
 .github/workflows/ci.yml                    |   8 ++
 src/frob/check/__init__.py                  |   4 +-
 src/frob/gates/__init__.py                  |  11 +-
 tests/conftest.py                           | 169 +++++++++++++++++++++++++---
 tests/gates_suite/test_run.py               |  47 ++++++++
 tests/unit/test_check_admission.py          |  12 +-
 tests/unit/test_conftest_midrun_watchdog.py | 138 +++++++++++++++++++++++
 tickets/T-3707/ticket.md                    |  97 +++++++++++++++-
 8 files changed, 454 insertions(+), 32 deletions(-)
```

### Evidence
- `tests/gates_suite/test_run.py::TestProcessPoolGates::test_run_gates_leaves_no_live_pool_threads_or_children_behind` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestTotalBudgetExceeded::test_true_at_exactly_the_budget` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestRunMidrunWatchdogTotalBudget::test_fires_total_budget_exit_with_no_stall_threshold_armed` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestAnnounceTotalBudgetExceededAndHardExit::test_hard_exits_with_status_1_and_prints_the_inventory_line` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 7 error(s), 4507 warning(s), 918 waived
- error-findings: COV007@.claude/hooks/frob-timeout-guard.py, DEPR006@frob-deprecated-baseline.lock.json, DUP001@tests/conftest.py, PRE001@tickets/T-3707, TICK003@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json

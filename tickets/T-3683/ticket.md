---
id: T-3683
title: 'win32 round 19: pre-lock stop points + mid-run watchdog'
state: queued
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
- tests/conftest.py
- src/frob/check/__init__.py
- src/frob/process/_guard.py
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
- docs/modules/process.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/process/_derived_lock.py
  reason: T-3681 holds a live lease on this file; narrow now and re-add only if the
    round-19 bisect actually names this file, once T-3681 has landed
  actor: logan
  at: '2026-09-01'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33582058515's round-18 instrumentation delivered decisive data.

BISECT: all four FROB_CHECK_STOP_BEFORE points from T-3675 are DIRTY --
stop-before lock/detect/tasks/submit all exit 130, each printing its
own "FROB-CHECK-STOP-BEFORE: reached '<point>' ... exiting cleanly"
line and THEN catching T-3648-SIGNAL during the clean exit (at a
threading wait / _weakrefset add). Combined with (e) trivial-python and
(f) import-only both CLEAN from the SAME run, the sender is bracketed
to pipeline SETUP between `import frob` returning and reaching the
FIRST stop point "lock" (which fires after every pipeline-wide scope/
lock is already acquired). The SIGINT is ALREADY PENDING by the time
the lock scope is acquired -- delivered during App(cfg)()/dispatch/
run_check's own pre-lock setup, or the lock-scope acquisition itself.
src/frob/process/_derived_lock.py's win32 msvcrt.locking backend
(active at/before "lock") is the prime candidate, alongside anything
touching the console during App/telemetry/config/dispatch setup.

HARD-EXIT DID NOT FIRE: the windows Test step again hit "exceeded
1500s" with NO "FROB-TEST-HARD-EXIT:" line -- pytest_sessionfinish was
never reached; the suite wedges BEFORE session finish, not at
teardown. Read together with round-17/18: pre-guard runs completed
~13k tests then died at teardown; now, with FROB_TEST_IGNORE_CONSOLE_
CTRL masking the interrupt, the suite instead HANGS mid-run -- a
`frob check` subprocess a test spawns (e.g. tests/test_cli_check.py)
gets the same in-pipeline SIGINT masked by ITS OWN inherited env and
then hangs on its own interruptible wait instead of dying, wedging the
parent test that is waiting on it.

Round 19 = two parts, within this ticket's declared scope (NOT
src/frob/__main__.py or src/frob/app/**, which are out of scope for
this agent -- if Part A's bisect brackets the sender into that
territory, this ticket files a follow-up rather than crossing scope).

PART A -- earlier stop points, bracketing inside src/frob/check/
__init__.py's own reach:
The current "lock" point fires only after `win32_console_ctrl_ignore_
scope()`, `_admission_budget(root)`, AND `derived_state_lock(root,
exclusive=False)` are ALL THREE already entered (a single `with (...)`
tuple). Restructure that into a `contextlib.ExitStack`-based sequential
entry (`stack.enter_context(...)` one at a time, same end state, same
locks held in the same order for a normal run) so 3 new stop points
can land BETWEEN each acquisition, in order:
  "entry"          -- before any context manager is entered at all (the
                      earliest point this module can instrument; if
                      DIRTY, the sender is at or before `run_check`'s
                      own call, i.e. in App construction/config
                      resolution/telemetry init/dispatch -- OUT of this
                      ticket's scope, file a follow-up naming exactly
                      that boundary)
  "console-scope"  -- right after win32_console_ctrl_ignore_scope()
                      enters (a no-op unless FROB_WIN32_IGNORE_CONSOLE_
                      CTRL is set, which these bisect variants do not
                      set), before _admission_budget
  "admission"      -- right after _admission_budget(root) enters,
                      before derived_state_lock
  "lock"           -- unchanged in meaning: after derived_state_lock
                      also enters (kept for round-18/19 continuity)
The existing "detect"/"tasks"/"submit" points are unchanged. Add 3 new
CI diag sub-variant steps (entry/console-scope/admission), same
Start-Process/uv harness as the existing 4. The EARLIEST DIRTY point
brackets the sender to the code between it and the previous CLEAN
point. If "admission" is clean and "lock" is dirty, `_admission_lock
_acquire_release_or_lock_scope_entry`/msvcrt.locking is directly
implicated -- confirm by auditing `src/frob/process/_derived_lock.py`'s
win32 backend (`portable_flock_acquire`/`portable_flock_release` in
`src/frob/process/_lock.py`, imported there) for anything that could
plausibly deliver a console ctrl event: GenerateConsoleCtrlEvent,
SetConsoleCtrlHandler, a signal-adjacent handle operation, or a
subprocess/handle call hidden inside the locking path -- and fix
whatever is found. If "entry" itself is dirty, do NOT attempt a fix in
this ticket (out of scope) -- file the precise follow-up instead,
naming the bracket this round narrowed to.

PART B -- mid-run watchdog (tests/conftest.py):
The T-3675 hard-exit only fires from `pytest_sessionfinish`, which a
mid-run wedge (a hung subprocess a test is blocked on) never reaches.
Add an independent, env-gated (FROB_TEST_MIDRUN_WATCHDOG_SECONDS=<N>,
a numeric threshold, unset/0/non-numeric = disabled) background
watchdog thread, started from `pytest_configure` (controller-only,
same early-return-on-`workerinput` posture every other controller-only
mechanism in this file already uses) and stopped from `pytest_
sessionfinish` (same `stop_event.set()` pattern T-3608's own stall
watchdog uses). Polls periodically; if NO test call-phase has reported
progress (`_last_progress_ts`, already tracked by the existing T-3608
`pytest_runtest_logreport` hook, reused here rather than duplicated)
for >= the threshold since either the watchdog started OR the last
observed progress, it prints a `SUITE-RESULT: MIDRUN-WATCHDOG-STALL`
line plus T-3675's own `_describe_teardown_blockers()` inventory line
(reused, not duplicated), flushes, and `os._exit(1)`s -- the SAME
hard-exit shape T-3608's `_announce_stall_and_abort` and T-3675's
`_maybe_hard_exit_after_session_finish` both already use, applied to a
THIRD wedge class (mid-run, no xdist crash marker, no session-finish
reached). Unlike T-3608's stall watchdog (which requires a recorded
xdist worker crash AND is xdist-only), this one requires neither --
gated purely on elapsed wall-clock time, so it also covers the current
`-p no:xdist` serial windows Test step. Unit-test the gating/threshold
parsing and the stall predicate the same way T-3608's own `_stall_
detected` is unit-tested.
Set FROB_TEST_MIDRUN_WATCHDOG_SECONDS to a value comfortably inside
the windows Test step's existing 1500s budget (e.g. 300) in .github/
workflows/ci.yml's windows Test step env: block, alongside FROB_TEST_
IGNORE_CONSOLE_CTRL/FROB_TEST_HARD_EXIT, with a comment explaining
this is diagnostic-first: once Part A's fix (if in-scope) or follow-up
(if not) clears the in-pipeline sender, subprocess frob-check calls
inside tests should neither get interrupted nor hang, and this
watchdog should stop firing in practice -- but stays armed so a future
wedge is never again a silent 1500s timeout with zero diagnostic
output.

References: T-3675 (round 18, filed the FROB_CHECK_STOP_BEFORE knob
and FROB_TEST_HARD_EXIT this round extends/restructures), T-3673
(round 17, filed FROB_TEST_IGNORE_CONSOLE_CTRL, the masking mechanism
whose side effect round 18 surfaced), T-3648 (signal logger + diag
scaffolding origin).

Scope: tests/conftest.py + src/frob/check/__init__.py +
src/frob/process/_derived_lock.py + src/frob/process/_guard.py +
.github/workflows/ci.yml + tests/test_ci_workflow_matrix.py +
docs/modules/process.md.
Explicitly OUT of scope (do not touch): src/frob/graph/cache.py,
tests/gates_suite/**, src/frob/refactor/**, src/frob/__main__.py,
src/frob/app/**, the ticket-runner concurrency tests (sibling series).

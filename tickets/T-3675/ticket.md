---
id: T-3675
title: 'win32 round 18: teardown hard-exit escape hatch + pipeline sender bisect'
state: in-progress
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
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
- docs/modules/process.md
- tests/unit/test_conftest_hard_exit_guard.py
- tests/unit/test_check_stop_before.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_conftest_hard_exit_guard.py
  reason: unit tests for FROB_TEST_HARD_EXIT (Part 1) and FROB_CHECK_STOP_BEFORE (Part
    2) gating logic
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_check_stop_before.py
  reason: unit tests for FROB_TEST_HARD_EXIT (Part 1) and FROB_CHECK_STOP_BEFORE (Part
    2) gating logic
  actor: logan
  at: '2026-09-01'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33556847222's round-17 results resolve the matrix decisively:
  (e) trivial-python:  CLEAN (exit 0, no T-3648-SIGNAL, 5.2s)
  (f) import-only:      CLEAN (exit 0, no T-3648-SIGNAL, 5.6s)
  (a)-(d):               all DIRTY (SIGINT, ~1.3-1.5s)
  (a2) mitigation:      GENUINE gate result, exit 1 at 9.0s, no SIGNAL

Both controls clean while every check-pipeline variant is dirty proves
the sender is INSIDE run_check's own pipeline, strictly after `import
frob` returns and strictly before the interruptible lock wait -- not
the environment, not frob's import machinery. (a2) validates the
FROB_WIN32_IGNORE_CONSOLE_CTRL mitigation end to end (T-3657, checked
by T-3673): a real, non-130 gate result with the scope active.

NEW DISCOVERY, orthogonal to the sender hunt: with the T-3673 suite
guard (FROB_TEST_IGNORE_CONSOLE_CTRL) armed, the windows Test step
stopped dying by KeyboardInterrupt -- and instead HUNG past the 1500s
step budget, terminated with orphan pytest/python processes still
alive ("Windows Test step exceeded 1500s with no completion"). Read:
the injected SIGINT was MASKING a real teardown wedge all along -- a
non-daemon thread or unreaped child blocks interpreter/session
teardown, and the interrupt (dying via KeyboardInterrupt) was
incidentally what broke that join and ended the step, however
destructively. Previous runs completed ~13k tests in ~1000s and only
then got interrupted at teardown -- the tests themselves finish fine;
only the SESSION-LEVEL teardown after the last test wedges.

Round 18 = two parts.

PART 1 -- suite teardown hard-exit (tests/conftest.py):
Add an env-gated (FROB_TEST_HARD_EXIT=1) escape hatch in
pytest_sessionfinish (after the SUITE-RESULT line and exit-status
handling this hook already does, so the summary is always written and
exitstatus is known) that flushes stdout/stderr and os._exit()s with
the session's real exit code -- T-3608's `_announce_stall_and_abort`
already establishes this exact os._exit pattern in this same file (the
same flush-then-os._exit shape, reused, not reinvented). Before
exiting, print ONE line inventorying live non-daemon threads
(threading.enumerate(), name + daemon flag) and known child processes
(multiprocessing.active_children(), name + pid) so every run that hits
this path documents WHAT was blocking teardown, not just that
something was. Gated OFF by default everywhere; set ONLY in
.github/workflows/ci.yml's windows Test step.
Acceptance: the next windows run's Test step completes with a genuine
SUITE-RESULT exit code (0 or 1) printed and the step exiting on it,
instead of a 1500s Wait-Process timeout.
Unit-test the gating logic and the inventory-line formatting the same
way T-3673 unit-tested FROB_TEST_IGNORE_CONSOLE_CTRL's gate (a fresh
`load_conftest_module` import, monkeypatched env/platform, asserting
on the printed inventory line's shape) -- do not require an actual
os._exit in the test itself (unit-test the composed inventory string
and the gating predicate directly; a real os._exit test would kill the
test runner).

PART 2 -- pipeline sender bisect (src/frob/check/__init__.py):
Add an env-gated FROB_CHECK_STOP_BEFORE=<point> debug knob to
`_run_check_with_skips`/`_run_tasks_concurrently` that exits the
pipeline cleanly (a trivial successful CheckResult / empty results
list, printing a breadcrumb naming the point) immediately before each
of 4 named points, bracketing the executor.submit/t.start() stack
frame T-3670's diag caught the interrupt at:
  "lock"   -- right after win32_console_ctrl_ignore_scope/admission_
             budget/derived_state_lock are all acquired, before the
             integrity/staleness/autofix prechecks run
  "detect" -- right after `_resolve_only` (config/only-flag
             resolution), before reset_parse_cache's memo scope opens
  "tasks"  -- right after `_python_tasks(...)` builds the task list,
             before `_collect_results`/`_run_tasks_concurrently` ever
             runs
  "submit" -- inside `_run_tasks_concurrently`, immediately before the
             `with concurrent.futures.ThreadPoolExecutor()` block --
             the last point before any thread actually starts
Env-gated, harmless everywhere else (same posture as
FROB_DISABLE_EXEC/FROB_DISABLE_POOL_PRELOAD/FROB_WIN32_SPAWN_DEBUG in
src/frob/process/_guard.py) -- unit-tested for each of the 4 points
(gating predicate + early-return shape), never wired into any default
code path.
Then extend .github/workflows/ci.yml's windows diag section with 3-4
new sub-variant steps, each the SAME diag script/fixture as variant
(a) but with FROB_CHECK_STOP_BEFORE=<point> set for one of the 4
points above. The EARLIEST stop point where T-3648-SIGNAL disappears
brackets the sender to the code between that point and the previous
(still-dirty) one.
Also grep `_run_check_with_skips`'s pre-thread-start code path (and
whatever it calls before `_run_tasks_concurrently`'s executor block)
for anything win32-signal-adjacent -- faulthandler timers,
`signal.set_wakeup_fd`, native/tree-sitter extension loads,
`msvcrt`-family locking -- and note any candidates found (or their
absence) directly in this ticket's body/Done report; this is
observational, not itself a scope item to fix.

References: T-3673 (round 17, filed the e/f/a2 controls and the
suite-guard mechanism this round's Part 1 hard-exit builds on), T-3670
(round 16, filed the a-d matrix these round-17 results resolve).

Scope: tests/conftest.py (hard-exit escape hatch, env-gated) +
tests/unit/ (new unit tests for both parts, not tests/gates_suite/**)
+ src/frob/check/__init__.py (FROB_CHECK_STOP_BEFORE knob only) +
.github/workflows/ci.yml (windows Test step env var + new diag
sub-variant steps) + tests/test_ci_workflow_matrix.py + docs/modules/
process.md.
Explicitly OUT of scope (do not touch): src/frob/graph/cache.py,
tests/gates_suite/**, src/frob/refactor/**.

---
id: T-2991
title: frob subprocess children spawned by system tests can be orphaned when their
  pytest worker is killed
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/conftest.py
- tests/system/test_run_helper_env_leak.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_run_helper_env_leak.py
  reason: PDEATHSIG + process-group-kill fix to run() needs test coverage alongside
    its existing test class in this file
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/system/test_run_helper_env_leak.py
  reason: PDEATHSIG + process-group-kill fix to run() needs test coverage alongside
    its existing test class in this file
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2980 fixed the CI hang by bounding tests/system/conftest.py's run()
default timeout so a wedging test fails loudly instead of hanging
forever. That fix does NOT address the deeper defect it uncovered:
when a system test's `frob` subprocess child does not exit on its
own, it becomes an ORPHAN once the timeout kills the test/worker,
because subprocess timeout expiry (or pytest-timeout's os._exit(1)
on the parent) does not guarantee the child is killed too in every
path.

Evidence: the real ubuntu-latest incident (run 32968539246, job
98176563537) ended with ten orphaned processes at GitHub Actions
cleanup -- uv, pytest, and eight pythons, pids spanning 5821 to
37282 (spawned across the whole run, not all at once):

    Cleaning up orphan processes
    Terminate orphan process: pid (5821) (uv)
    Terminate orphan process: pid (5824) (pytest)
    Terminate orphan process: pid (5825) (python)
    Terminate orphan process: pid (5828) (python)
    Terminate orphan process: pid (5834) (python)
    Terminate orphan process: pid (23329) (python)
    Terminate orphan process: pid (26058) (python)
    Terminate orphan process: pid (26615) (python)
    Terminate orphan process: pid (37281) (python)
    Terminate orphan process: pid (37282) (python)

I reproduced the mechanism locally with a minimal pytest-xdist +
--dist=loadgroup fixture: killing a worker via pytest-timeout's
thread method (os._exit(1)) leaves the worker's own subprocess.run()
child (a `sleep 300` stand-in) running as an orphan -- confirmed via
pgrep after the run exited.

This repo has hit this class before (T-2443: 94 orphaned frob check
forkservers held 17GB of swap and presented as "no progress"), and
arm_parent_death_signal's PDEATHSIG protection is Linux-only and was
reworked twice recently (T-2880, T-2936) -- worth checking whether it
covers the tests/system/conftest.py::run() subprocess path at all.

PLAN (not prescriptive, just leads): audit whether frob subprocess
children spawned by tests/system's run() register for
PDEATHSIG/process-group cleanup; consider having run() kill the
child's whole process group on TimeoutExpired (subprocess.run's
default timeout handling only kills the direct child, not
grandchildren spawned by a forkserver); verify with a local
xdist+loadgroup repro like the one used to diagnose T-2980 before
closing.

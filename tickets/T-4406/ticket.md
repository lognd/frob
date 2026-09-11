---
id: T-4406
title: 'scaffolded python-tool project fails frob check on Windows: pytest collect-only
  exits 2 (COV003)'
state: queued
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: v0.531.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_scaffold_dx.py
- src/frob/scaffold/*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34546329688, Windows leg only.

Node id: tests/system/test_scaffold_dx.py::test_python_toolchain_scaffold_passes_check_immediately[python-tool]

Assertion (verbatim):
    assert check.returncode == 0, check.stdout + check.stderr
E   AssertionError: frob check .  [FAIL]  1 error  9 warnings
E     ## Errors
E       [gate:COV] pytest --collect-only:0  COV003  COV003: pytest collection itself
        failed -- every Python evidence id is unresolved as a consequence of this ONE
        root cause, not independently broken; run frob doctor (T-1161's venv-shim
        shebang scan may name the fix) and re-run uv run pytest --collect-only by
        hand to confirm. ...python.exe -m pytest --collect-only -q -rs -o addopts=
        (cwd=.) exited 2
E     stderr tail:
E     process: arm_parent_death_signal: PR_SET_PDEATHSIG has no equivalent on win32 --
        forkserver orphan-reaping via parent-death signal is disabled on this platform
        (T-2944)
E     process: forkserver helper pid=4388 could not arm PR_SET_PDEATHSIG --
        launcher-death leak NOT closed for this run (non-Linux platform or prctl
        failure)

This is a distinct mechanism from T-4367 (tool-absence classifier) -- ruff
is not implicated here, and this is a freshly scaffolded project (the
scaffold_dx test-suite type this repo generates for a new "python-tool"
project), not this checkout. pytest --collect-only exits 2 inside the
scaffolded venv on Windows, so COV003 fires and blanks every evidence id.
Root cause not yet isolated; candidates: (a) the T-1161 venv-shim shebang
scan the error message points at not covering the scaffolded venv shim on
win32, (b) the forkserver PR_SET_PDEATHSIG warnings being a red herring
vs. a genuine collection-time exception (need the actual pytest stderr,
which this repr truncates). Fix needs the Windows mirror: reproduce the
pytest --collect-only invocation inside a scaffolded python-tool project
on win32, read the real traceback, then make production code
platform-correct (declared sys.platform reason) rather than papering over
the assertion.

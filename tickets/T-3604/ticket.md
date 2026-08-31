---
id: T-3604
title: 'Windows diag step: typeless fixture fast-fails CHECK001 and aborts job before
  Test step (T-3589 round 7)'
state: queued
kind: bug
origin: human
created: '2026-08-31'
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
Run 33439890956 (first with T-3597's --project fix): the T-3589 diagnostic
step no longer hangs and no longer dies with ModuleNotFoundError -- frob
check COMPLETED on win32 in 547ms. But it exited 1 with:

  CHECK001 unknown project type: 'unknown' (no dispatchable language stage)  (x2)

because the fixture is a bare src/demo/__init__.py + git init with NO
pyproject.toml, so project detection legitimately yields 'unknown'. The
step then propagated exit 1 and ABORTED the windows job at ~4min -- the
Test step never ran this run.

Three fixes, same step in .github/workflows/ci.yml:
1. Make the fixture a real Python project: write a minimal pyproject.toml
   (name/version/build nothing fancy) next to src/demo so frob classifies
   it and actually dispatches a language stage.
2. Distinguish outcomes: the watchdog dump (faulthandler at 240s) is the
   only true-failure signal; a CLEAN gate result OR ordinary gate errors
   both mean 'no hang' and the step should succeed (print and exit 0).
   Keep the output loud either way.
3. The step must not gate the job: `continue-on-error: true` on this one
   step so the Test step always runs (windows job is advisory anyway,
   but the Test step is the data we want every run).

Also observed: --budget 180 ran only gates-fast+gates-native, deferring
gates-security, lint, static. The suite's real hang (test_cli_check.py:67
child) may live in a DEFERRED stage. After fix 1, if the diag still shows
no hang, raise/remove the budget in the diag so all 5 stage groups run on
the fixture -- that is the actual reproduction attempt.

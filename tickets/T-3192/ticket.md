---
id: T-3192
title: 'A hanging CI job produces no failure signal: turn ubuntu hangs into timed
  failures with stack dumps'
state: queued
kind: bug
origin: human
created: '2026-08-27'
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
scope_changes:
- op: add
  glob: .github/workflows/ci.yml
  reason: per-job timeout and faulthandler wiring
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
STRUCTURAL. The ubuntu-latest job hangs and produces NO failure signal. The
owner cancelled run 33135896391 by hand after 54 minutes. This is at least the
third such cancellation: run 33032904841 and run 32968539246 (2h40m) are both
recorded `cancelled`, not `failure`.

WHY THIS IS THE WORST OF THE THREE CI PROBLEMS. A hang is not a red build. It is
an ABSENT build. It occupies the exact ambiguity this project has repeatedly
identified as its dominant bug class: a result that is simultaneously
"not-failed" and "not-measured", rendered identically to a pass by every
consumer that only looks for `failure`. Nobody can triage a job that never
finished, the run must be killed by a human, and the underlying defect stays
invisible for as long as that persists. T-2992 exists to triage what the hang is
HIDING; this ticket is about the hang being undiagnosable AT ALL.

WHAT TO BUILD:

  1. A per-job timeout that turns a hang into a FAILURE with evidence, rather
     than an unbounded run a human must cancel. `timeout-minutes` on the job is
     necessary but NOT sufficient -- a bare timeout gives a red X and no
     information, which is barely better than a cancel.

  2. A STACK DUMP at the timeout boundary. This project already has the recipe:
     `PYTHONFAULTHANDLER=1` plus `timeout -s ABRT <N>` dumps every thread's
     stack from a stuck process in one command. Wire that into the CI test
     invocation so the timeout produces the frames where it is wedged. That
     converts "ubuntu hangs" -- a statement no one can act on -- into a named
     function and line.

  3. Make the timeout budget explicit and justified, not guessed. The macOS job
     completed its Test stage in ~23 minutes; ubuntu ran 54+ without finishing.
     Pick a ceiling from the observed distribution and state it.

CANDIDATE CAUSES TO RULE IN OR OUT (measure, do not assume -- and note this
project has repeatedly produced tickets whose stated cause was never verified):
  - A test that waits on a lock, a subprocess, or a monitor with no timeout of
    its own. The land/lease machinery is full of waits and this repo has already
    seen agents park forever on a monitor.
  - Multiprocessing forkserver children outliving their parent. 94 orphaned
    forkserver processes holding 17GB were observed on the dev box in this same
    project; the same leak in CI would present exactly as a hang.
  - An xdist worker that dies while the controller waits.
  - A test that reads stdin, or a subprocess prompting for input that never
    arrives.

DO NOT "FIX" THIS BY SHORTENING THE SUITE OR SKIPPING TESTS ON UBUNTU. Reducing
coverage until the hang stops reproducing converts a diagnosable defect into a
permanent hole, and a truncated run is a DIFFERENT question, never a smaller
answer.

ACCEPTANCE
- A hanging ubuntu job now fails within a stated budget instead of running until
  a human cancels it.
- The failure output names where it was stuck -- a stack dump, not just a
  timeout message. Demonstrated on a deliberately planted hang (positive
  control); a timeout path that has never fired is not known to work.
- The timeout budget is justified from measured job durations.
- The actual ubuntu hang cause is identified and either fixed here or filed with
  the stack evidence attached, so T-2992's triage finally has something to read.

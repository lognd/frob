---
id: T-2715
title: 'Deferred verification is deadlocked: the 480s budget is 12s short of the tool''s
  own recorded 492s stage total'
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/_check_chunking.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_check_budget.py
- tests/unit/test_app_ticket_land.py
- docs/modules/tickets-verify-sweep.md
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_check_chunking.py
  reason: 'T-2715: derive post-land sweep budget from measured stage timing instead
    of a hardcoded ceiling'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-2715: derive post-land sweep budget from measured stage timing instead
    of a hardcoded ceiling'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'T-2715: derive post-land sweep budget from measured stage timing instead
    of a hardcoded ceiling'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_check_budget.py
  reason: 'T-2715: derive post-land sweep budget from measured stage timing instead
    of a hardcoded ceiling'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: tests/unit/test_app_ticket_land.py
  reason: 'T-2715: derive post-land sweep budget from measured stage timing instead
    of a hardcoded ceiling'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'T-2715: doc targets for touched land-sweep budget functions'
  actor: logan
  at: '2026-08-20'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-2715: doc targets for touched land-sweep budget functions'
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: record the discriminating second measurement that separates this budget
    shortfall from T-2713's resume-file defect
  actor: logan
  at: '2026-08-20'
  old_length: 3415
  new_length: 4868
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Verification can no longer complete, at all

Measured 2026-08-20, immediately after T-2713 landed.

`frob verify now` on a 3-entry queue:

    WARNING: `frob check --json --budget` run reported no BUDGET001 deferral
    of its own, but 4 stage group(s) (gates-fast, gates-native,
    gates-security, lint) never executed THIS invocation at all
    ERROR: verify worker: unmeasurable verification at 2d5ab2161d63 --
    watermark and queue left untouched, will retry on the next wake
    ERROR: verify now: Unmeasurable

T-2713's refusal is CORRECT and must not be reverted -- refusing to
advance on an unmeasured run is the whole point. The problem is that the
run can now never be measured, so the queue can never drain and the
watermark can never advance again.

## Arithmetic

`.frob/check-budget-timing.json`, the tool's own recorded stage timings:

    gates-fast       168.49
    gates-native      88.48
    gates-security   135.35
    lint               3.69
    static            96.17
    -------------------------
    total            492.18

`_POST_LAND_SWEEP_BUDGET_S = 480` (`src/frob/app/ticket_runner/_land_cmd.py:563`).

The budget is ~12s SHORT of the work it must cover. Not a contention
effect -- a structural shortfall against the tool's own measurements.

## Root cause: a threshold calibrated once, never re-derived

The constant's own comment states the calibration basis:

    "the common case measures ~131-220s wall time for the parts of the
    split this ticket measured directly"

That was true when written. The repo has since grown to 492s of stage
work. The budget did not move with it, and nothing detects the drift --
so a number chosen as generous headroom silently became a hard ceiling.

## Why T-2713 did not cause this

Before T-2713, the same shortfall existed but was INVISIBLE: the
truncated run was rendered GREEN and the watermark advanced anyway (it
recorded 2 of 40 real error identities). T-2713 converted a silent
false-green into a loud refusal. The underlying inability to complete
was always there. Do not "fix" this by relaxing T-2713.

## Fix directions, in preference order

1. Derive the budget from the recorded stage timings with real headroom
   (e.g. total * 1.5) instead of hardcoding it, so it tracks repo growth.
   A hardcoded number will drift again.
2. If a hardcoded ceiling must remain, add a check that FAILS LOUDLY when
   recorded total time approaches it, rather than waiting for the
   unmeasurable refusal to surface it.
3. Consider whether the deferred verification should be budgeted at all.
   It runs detached, off the land critical path; a budget that can
   silently drop coverage buys little there.

Note the 540s shell cap that agents run under is a DIFFERENT limit and
already exceeds 492s. This budget is self-imposed.

## Positive controls, both directions

- with the fix, `frob verify now` on a backlog COMPLETES, advances the
  watermark, and records a baseline whose identity count matches an
  independent unbudgeted `frob check --json`
- a genuinely unmeasurable run (e.g. a killed stage) STILL refuses to
  advance -- T-2713's guarantee must survive intact
- the recorded-total-vs-budget check fires BEFORE the deadlock, on a tree
  whose timings approach the ceiling

## Immediate operational note

The verify queue is stuck right now and will stay stuck until this lands.
Post-land regression detection is not running.




## CONFIRMED by a second, discriminating measurement (2026-08-20)

The first observed failure could have been either this budget shortfall
or T-2713's resume-file bug. A second `frob verify now`, run after
T-2713 landed and against a fresh resume state, discriminates them --
and BOTH are real, independent defects:

    WARNING: `frob check --json --budget` run deferred 1 stage group(s)
    (static) -- error-finding identities are unmeasured, not a partial set
    ERROR: verify worker: unmeasurable verification at dd22aa95dc00 --
    watermark and queue left untouched

This run reported a GENUINE BUDGET001 deferral of exactly one group,
which is the arithmetic in this ticket rather than T-2713's mechanism:

    ran:       gates-fast 168.49 + gates-native 88.48
             + gates-security 135.35 + lint 3.69   = 396.01
    remaining: static 96.17                        -> 492.18 total
    budget:                                           480.00

So with a clean resume state the run still cannot fit, and `static` is
deferred every time. T-2713's fix correctly refuses to advance on it.

DISTINCTION TO PRESERVE: T-2713 fixed a run whose `deferred` list read
EMPTY while 4 groups silently never executed (a stale narrow resume file).
This ticket is a run that HONESTLY reports deferring `static` because the
work genuinely exceeds the budget. Fixing one does not fix the other, and
T-2713's guarantee must survive whatever is done here.
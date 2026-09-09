---
id: T-4363
title: Coverage stamp step is budgeted 120 min but the job only has 117 left
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: critical
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
THE LINUX JOB CANNOT FINISH ITS LAST STEP, BECAUSE THAT STEP IS BUDGETED MORE TIME
THAN THE JOB HAS LEFT TO GIVE IT.

MEASURED, FROM THE FIRST RUN THAT EVER REACHED THIS STEP:

  job timeout-minutes ......... 150   -> job is killed 150 min after it starts
  job started ................. 02:56:25   -> hard kill at 05:26:25
  the step started ............ 03:29:34   -> 33 minutes into the job
  the step's own deadline ..... 7200s = 120 min  -> it expects until 05:29:34

So the step is allowed 120 minutes and can only ever receive 117. It is
structurally impossible for it to reach its own deadline; the job ceiling always
fires first, by roughly three minutes.

WHY NOBODY NOTICED UNTIL NOW. Every previous run failed at an earlier step, so
this one was always SKIPPED. The first run to get this far is the first run that
could expose it -- which means this defect has been latent for as long as the
budgets have been out of step, and would have surfaced at exactly the moment
everything else finally went green.

THE STEP-LEVEL TOLERANCE DOES NOT SAVE IT. The step is marked continue-on-error,
so a step FAILURE would be survivable by design. A JOB timeout is not: it kills
the job whatever the step's tolerance says. The tolerance therefore creates a
false sense of safety around a step that cannot fail gracefully.

WHAT THE STEP IS ACTUALLY DOING, and this is the part to think about rather than
just re-tuning a number. It re-runs the entire suite under coverage, pinned to two
workers, AFTER the same suite has already run once in this job. So the job pays
for the test suite twice, the second time deliberately slowed. That may be the
right trade for a coverage stamp, but it should be a decision someone made
knowingly, not an accident of two budgets drifting apart.

DECIDE BETWEEN THE REAL OPTIONS RATHER THAN NUDGING THE CEILING:
  - Give the job enough headroom that the step's own deadline is the binding
    constraint, so the step can fail honestly instead of taking the job down.
  - Cut the step's cost so it fits comfortably -- more workers, a narrower scope,
    or reusing the first run's data instead of re-running the suite.
  - Move it off the per-push path entirely, onto a schedule or a release gate,
    if a fresh coverage stamp is not something every push needs.
Whichever you choose, the invariant to state and enforce is that a step's own
budget must be strictly smaller than the time the job can still give it. Consider
whether that relationship can be checked rather than maintained by hand -- two
numbers in different places that must agree is the shape that has bitten this
project repeatedly.

VERIFY by showing the linux job completing to its final step with the new
arrangement, and quote the elapsed time of this step against both budgets. A run
that merely gets further is not evidence; the step must terminate on its own
terms.

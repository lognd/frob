---
id: T-3888
title: WAIVE004 reports a live waiver as matching zero findings, and its remedy is
  to delete it
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Reported as stpone FROBLEMS F-010. Two lines of ONE `frob check` run contradict
each other, and the wrong one gives actively harmful advice.

MEASURED BY THE REPORTER:

    WAIVE004: include/stpalpha/hal/lcd.h:2 frob:waive PARSE002
              matches 0 findings this run

    ... while the SAME run's tool summary says:

    gate:PARSE  0 errors ... 3 waived

So the waiver matched three findings and suppressed them, and WAIVE004
simultaneously reported it as matching nothing. The reporter confirmed the
waiver is load-bearing: removing it brings PARSE002 back as an error.

THEIR DIAGNOSIS, which is probably right and must be verified rather than
assumed: WAIVE004 is evaluated against a pass that ran BEFORE the PARSE gate,
so at the moment it looks, the findings its waiver would match do not exist yet.

WHY THIS RANKS ABOVE ORDINARY FRICTION. WAIVE004 exists to find DEAD waivers so
they can be deleted -- it is a cleanup rule. When it fires falsely, its
remedy is "delete this waiver", and following that remedy on a live waiver
turns a suppressed finding into a build failure. The reporter says it plainly:
it "teaches agents to delete needed waivers". A rule whose false positive
instructs you to break the build is worse than a rule that stays quiet.

It is also the same shape as several defects found today: two parts of one run
disagreeing (fleet_status reporting a lease LEAKED while listing its live
worktree in the same output, T-3403), and a verdict computed from a stale or
partial view being presented as fact.

WHAT TO DO
  1. Confirm the ordering hypothesis with the actual execution order, not by
     inference -- name where WAIVE004 is computed relative to the gate whose
     findings it consumes.
  2. Compute WAIVE004 only AFTER every gate that can consume a waiver has run.
     If the current architecture cannot guarantee that (stages running
     concurrently, say), then WAIVE004 cannot be correct as a per-run rule and
     the honest answer is to say so and change what it claims -- do not leave a
     rule that is right only when the stage order happens to cooperate.
  3. While fixing, check the SYMMETRIC failure: can WAIVE004 also stay SILENT
     about a genuinely dead waiver because the consuming gate ran after it? A
     rule with an ordering bug usually has both polarities, and the silent one
     is worse -- an accumulating pile of dead waivers nobody is told about is
     exactly the drift WAIVE004 exists to prevent.

DO NOT fix this by suppressing WAIVE004 when a waiver's rule id was not run.
That is close to correct but subtly wrong: "the gate did not run" and "the gate
ran and matched nothing" are different facts, and collapsing them would make
WAIVE004 silent under `--only` runs where it could still be right. If a
distinction is needed, report the third state explicitly.

MUST-FIRE FIXTURE:   a genuinely dead waiver (its rule ran and matched nothing)
                     is still reported by WAIVE004.
MUST-STAY-QUIET:     a live waiver that suppressed findings in the same run is
                     never reported as matching zero.
THIRD FIXTURE:       a waiver whose rule did not run at all in this invocation
                     is reported as UNKNOWN/not-evaluated, not as dead.

ACCEPTANCE
- The ordering confirmed against real execution order, with file:line.
- WAIVE004 computed after its consumers, or its claim narrowed honestly.
- The symmetric false-silence case investigated and reported either way.
- All three fixtures committed.

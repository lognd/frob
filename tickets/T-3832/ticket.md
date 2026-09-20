---
id: T-3832
title: 'F-027: SYS112 ambient via-less grant fires in check SELFAUDIT but not frob
  sys audit -- waiver inconsistent'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: T-4665
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: v1.1.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4665
  reason: '2026-09-19: SF-16 in the STRATA friction audit; joins story B of epic T-4662
    -- one rule with two engines and two answers makes every other SYS measurement
    in this epic ambiguous'
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v1.1.0
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: '2026-09-19: attaching SF-16''s evidence row verbatim and the sequencing
    note that T-4672''s instrumentation is what would PROVE the two engines converge
    rather than asserting it'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1473
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## SF-16 evidence (attached 2026-09-19 by the STRATA friction epic, T-4662)

Recorded in scratchpad/STRATA-FRICTION.md as SF-16, evidence table row verbatim:

| SF-16 | Same rule, two engines, two answers: SYS112 fires under `check SELFAUDIT` but not `frob sys audit`; waivers disagree | tickets/T-3832/ticket.md (F-027, queued) | 1 rule, 2 engines | MEDIUM |

And verbatim from the SF-14/15/16/17 section:
"T-3832 (F-027): 'SYS112 ambient via-less grant fires in check SELFAUDIT but not
frob sys audit -- waiver inconsistent'. Queued. Fix surface: ONE ENGINE, NOT TWO."

NOW A CHILD OF T-4665 (story B of epic T-4662). This is the highest-leverage of
the four consumer-reported SYS defects, because it is the only one that makes
every OTHER SYS measurement ambiguous: while one rule can produce two answers
depending on which entry point asked, no finding count and no waiver is a
statement about the code. Per memory/silent-zero-is-the-dominant-bug-class.md,
a disagreement between two engines is how a silent zero hides -- the engine that
says nothing looks clean.

Sequencing note: T-4672 (SF-01) instruments the SYS slice so an evaluated-clean
rule becomes distinguishable from a never-evaluated one. Landing T-4672 first
gives this ticket the telemetry to PROVE the two engines agree afterwards,
rather than asserting it. Not filed as a hard blocker, because the engine
unification can be designed independently -- but do not claim convergence
without that evidence.

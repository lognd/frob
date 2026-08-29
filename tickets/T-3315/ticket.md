---
id: T-3315
title: frob ticket sweep refuses on a done ticket with no stated remedy after a post-close
  scope fix
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
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
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-036).

`frob ticket scope T-0015 --add ...` succeeds on an already-DONE ticket (a
legitimate post-close scope correction, e.g. tidying the record), but the
follow-up `frob ticket sweep T-0015` -- which the CLI's own remediation text
recommends after a scope change -- then exits 1 (FAST_EXIT1) because the
ticket is closed. The scope edit itself took effect and cleared SCOPE001, so
the sweep refusal is a dead end with no stated remedy: the fix already
worked, but the tool tells you to run a command that cannot succeed.

WHAT TO BUILD: either (a) `sweep` should be a genuine no-op success (exit 0,
"nothing to sweep, ticket is closed") on a done/dropped ticket rather than a
FAST_EXIT1 refusal, since a closed ticket has no more pre-work sweep to
perform and that is a legitimate, expected state -- not a failure; or (b) if
sweep must stay closed-refusing for a real reason, whatever remediation text
led the user to run it post-close in the first place should stop suggesting
it. Confirm which call site prints that suggestion before picking (a) or (b).

MUST-FIRE / MUST-STAY-QUIET: `frob ticket sweep <id>` on an in-progress
ticket behaves exactly as today; on a done/dropped ticket it either succeeds
quietly (0) or the remediation text that recommends it stops appearing for
already-closed tickets -- no more dead-end recommendation.

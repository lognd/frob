---
id: T-3944
title: 'F-174: scope --add invalidates the pre-work sweep without refreshing it, so
  PRE001 goes stale'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_mutate.py
- src/frob/gates/_prework.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/ticket_runner/_scope_cmd.py
  reason: the filed scope named src/frob/app/ticket_runner/_scope_cmd.py, which does
    not exist -- I invented the path instead of verifying it. scope --add is handled
    in _mutate.py and the pre-work sweep/PRE001 lives in gates/_prework.py
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: the filed scope named src/frob/app/ticket_runner/_scope_cmd.py, which does
    not exist -- I invented the path instead of verifying it. scope --add is handled
    in _mutate.py and the pre-work sweep/PRE001 lives in gates/_prework.py
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/gates/_prework.py
  reason: the filed scope named src/frob/app/ticket_runner/_scope_cmd.py, which does
    not exist -- I invented the path instead of verifying it. scope --add is handled
    in _mutate.py and the pre-work sweep/PRE001 lives in gates/_prework.py
  actor: logan
  at: '2026-09-06'
body_changes:
- mode: set
  reason: 'F-297 shows scope --remove invalidates the sweep too, not just --add, so
    the trigger is any scope MUTATION rather than growth -- a fix keyed on --add would
    leave --remove broken. Also notes the compounding: they were removing a leased
    doc, i.e. working around T-3949, which then tripped this'
  actor: logan
  at: '2026-09-06'
  old_length: 1991
  new_length: 3124
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-174, 2026-09-06:

  "T-0167 added design/vmodel.strata to scope after start and gates-fast
   reported PRE001 staleness until frob ticket sweep ran again. scope --add
   should refresh the pre-work sweep itself (or say 're-run sweep')."

THE DEFECT IS A BROKEN INVARIANT BETWEEN TWO PIECES OF STATE. The pre-work sweep
is a measurement OF the scope. Growing the scope invalidates that measurement,
but nothing connects the two, so the sweep silently describes a scope that no
longer exists and PRE001 fires on staleness the user did not knowingly create.

The user's remedy is discoverable only by hitting the error. That is the
"automatic over commands" doctrine again: a workflow that requires remembering a
follow-up command has a nonzero failure rate no documentation drives to zero,
and this one is a pure derived-state refresh with no judgement in it.

TWO ACCEPTABLE FIXES, IN ORDER OF PREFERENCE:
1. scope --add refreshes the pre-work sweep itself. Correct if the refresh is
   cheap and side-effect-free -- CHECK THAT FIRST, because a sweep that is slow
   or that writes into the shared root would make this the wrong answer, and
   this repo has measured both of those hazards before.
2. If (1) is genuinely unsafe, scope --add must SAY SO at the moment of the
   change -- naming the exact command to run -- rather than leaving the user to
   discover it from a later PRE001. Do not settle for (2) without establishing
   why (1) fails; "it seemed safer" is not a finding.

DO NOT fix this by relaxing PRE001. The staleness detection is correct and is
the only thing that caught this.

MUST-FIRE FIXTURE: scope --add followed immediately by gates-fast does not
report PRE001 staleness.
MUST-STAY-QUIET: a genuinely stale sweep (scope changed by some other route)
still trips PRE001 -- without this you cannot tell a refreshed sweep from a
disabled check.

ACCEPTANCE
- Which of the two fixes was taken, and the measured reason.
- Both fixtures committed.
## SECOND INSTANCE, THE OTHER DIRECTION: F-297

logand.app-v2, 2026-09-06: "Removing a leased doc from scope
(`frob ticket scope --remove`) made gate:PRE fire PRE001 (STALE PRE-WORK SWEEP)
and needed `frob ticket sweep` again: a scope change should refresh the sweep."

This ticket was filed from F-174, where `scope --add` invalidated the sweep. The
same defect fires on `--remove`. So it is not about GROWING the scope -- ANY scope
mutation invalidates the sweep, because the sweep is a measurement OF the scope
and nothing connects the two.

THAT SIMPLIFIES THE FIX AND SHOULD BE STATED IN IT: the trigger is "the scope
changed", not "the scope grew". A fix keyed on `--add` would leave `--remove`
broken and would have to be found again -- which is exactly what happened between
these two reports.

NOTE THE COMPOUNDING CONTEXT, because it makes this more than a papercut: the
consumer was removing a LEASED doc from scope, i.e. performing the workaround for
the lease-granularity defect (T-3949). So one open defect forced a scope
mutation, which tripped a second open defect, which cost another sweep. Neither
was their work.

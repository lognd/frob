---
id: T-4006
title: done-report and work report ERROR on their intended success paths, tripping
  frob's own FAST_EXIT1 heuristic
state: queued
kind: ux
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
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'apollo reported a third severity-mismatch instance with a distinct mechanism:
    a land raises a quarantine for the previous batch and clears it itself, so the
    ERROR is true when printed and false moments later. Recorded here because the
    class and cost match, with its different (timing, not static severity) mechanism
    called out'
  actor: logan
  at: '2026-09-06'
  old_length: 3701
  new_length: 5739
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer apollo, 2026-09-06 (r12). TWO INSTANCES OF ONE DEFECT: a SUCCESS path
reported as an ERROR.

INSTANCE 1 -- done-report in a worktree:
  "`frob ticket done-report` in a worktree prints ERROR ('recorded ONLY on this
   worktree's own branch') for what is actually the intended success path before
   a land. An INFO/WARNING would stop it reading as a failure; the FAST_EXIT1
   warning heuristic also fires on it."

INSTANCE 2 -- work on an already-started ticket:
  "`frob ticket work T-XXXX` on an already-started ticket errors AFTER creating
   the worktree ('worktree ready ... ERROR: already in-progress') -- the error is
   safe to ignore; the worktree is usable."

WHY THIS IS WORTH FIXING RATHER THAN DOCUMENTING. Both commands DID THE RIGHT
THING and then said ERROR. Instance 2 is the sharper one: it performed the work
successfully, produced a usable worktree, and then reported failure about it. A
consumer has now written down, in a file we read, that one of our errors is "safe
to ignore". That is the most expensive sentence a tool can provoke, because it
generalises: the next error they skip may be real.

IT ALSO BREAKS AUTOMATION, NOT JUST READING. FAST_EXIT1 -- frob's OWN heuristic
for "this exited with an ERROR fast, so it did NOT do the work you may think it
did" -- fires on instance 1. So an honest diagnostic built to catch silent
no-ops now misfires on a documented success path, which degrades that heuristic
for every real case. And an agent or script branching on exit status cannot
distinguish these from genuine failures.

THIS IS A MEASURED HAZARD FOR US SPECIFICALLY. This session lost roughly an hour
to an agent that could not tell a slow success from a failure, and I myself read
a failed argparse call as success by looking at output text instead of an exit
code. Severity that does not match outcome makes both mistakes easier.

WHAT TO DETERMINE FIRST, per instance -- they may need different answers:
  - Instance 1: is worktree-local recording genuinely the intended pre-land
    path? If yes, it is INFO (or at most WARNING with a "this is expected before
    a land" clause), and the exit status must be success. If there is a case
    where it IS an error, distinguish the two rather than flattening both to
    INFO.
  - Instance 2: decide whether `work` on an already-started ticket is an error
    at all. If the worktree is usable and that is the desired outcome, it is
    success with an informational note. If it is genuinely a misuse, then it
    must NOT create the worktree first -- doing the work and then refusing is
    the worst of both. EITHER OUTCOME IS ACCEPTABLE; the current mixture is not.

DO NOT fix this by softening the text while leaving the exit status non-zero.
The exit status is what scripts and the FAST_EXIT1 heuristic read; prose alone
does not resolve it.

WORTH A WIDER SWEEP WHILE HERE: grep for other paths that log at ERROR and then
return success, or return non-zero after completing their work. Two instances
reported in one wave suggests a pattern rather than two accidents. Report what
the sweep finds even if you only fix these two.

MUST-FIRE FIXTURE: a genuine done-report failure still reports ERROR and a
non-zero status.
MUST-STAY-QUIET: the normal pre-land worktree done-report path reports success,
and FAST_EXIT1 does not fire on it.
THIRD FIXTURE: `frob ticket work` on an already-started ticket has ONE consistent
outcome -- either success with a usable worktree, or refusal with no worktree
created.

ACCEPTANCE
- Severity and exit status agree with outcome for both commands.
- FAST_EXIT1 no longer fires on a documented success path.
- The wider sweep reported.
- All three fixtures committed.
## THIRD INSTANCE, and it is the most alarming shape yet

apollo, 2026-09-06:

  "A land can RAISE a quarantine mid-run for the PREVIOUS batch (TEST006 on the
   stamp) and then CLEAR IT ITSELF when its own reverify passes -- the scary
   ERROR line is transient; check `frob verify status` before reacting."

The two instances above are success paths mislabelled as ERROR. This one is
worse: an ERROR that is TRUE WHEN PRINTED and FALSE MOMENTS LATER, resolved by
the same run that raised it. The user is shown a quarantine -- one of the
loudest states this system has -- for a condition the run is about to fix on its
own.

WHY IT BELONGS ON THIS TICKET RATHER THAN ITS OWN: the defect is identical in
kind -- output whose severity does not describe the outcome -- and the cost is
the same, which is that a consumer has now written down a SECOND "safe to ignore"
instruction, this time for a QUARANTINE. That is the state we most need people to
react to. Teaching users to wait-and-see through a quarantine line is a direct
attack on the mechanism's purpose.

IT ALSO HAS A DISTINCT MECHANISM, so do not assume this ticket's fix covers it:
the other two are a static severity choice on a known-good path. This is a
TIMING problem -- a transient intermediate state made externally visible. The
candidate fixes differ accordingly: do not surface a quarantine raised for a
previous batch until the current run's reverify has settled, or label it
explicitly as provisional ("raised for the previous batch; will clear if this
run's reverify passes") so the reader knows it is not yet a verdict.

THE CONSUMER'S OWN REMEDY IS THE TELL: "check `frob verify status` before
reacting". A user needing a SECOND command to find out whether the first
command's ERROR was real is the definition of an unreliable signal.

ADDITIONAL FIXTURE: a quarantine raised and self-cleared within one run is
either not surfaced as an ERROR at all, or is surfaced as explicitly provisional
-- and a quarantine that genuinely persists past the run is still loud.

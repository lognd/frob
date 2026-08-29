---
id: T-3399
title: 'TICK004 errors on healthy decomposed epics: the rule prints ''already decomposed
  and being worked'' and reports an error anyway'
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
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
MEASURED 2026-08-29. TICK004 reports three of its four current findings against
tickets its own message says are HEALTHY.

    T-0969 (high, epic)      33d queued -- "already decomposed and being worked
                                           (a non-terminal child ticket carries
                                           parent=T-0969); the age is real and
                                           still worth noting, but the
                                           recommended action is checking the
                                           children's own progress instead"
    T-1273 (high, epic)      31d queued -- same
    T-1686 (critical, epic)  23d queued -- same

The rule already KNOWS these are decomposed. It computes the fact, writes it into
the finding text, recommends looking at the children instead -- and then reports
an ERROR anyway.

WHY THAT IS WRONG. An epic sits `queued` BY DESIGN while its children are worked
and landed. That is the intended lifecycle, not rot. Under the current rule every
healthy decomposed epic becomes a permanent ERROR the moment it passes the age
threshold, and the only ways to silence it are to churn its priority, drop it, or
close it falsely -- all of which corrupt the ledger to satisfy a gate.

This matters right now because these three errors are part of the set gating an
imminent release, and the "fix" available to a release engineer under time
pressure is exactly the ledger corruption above.

THE FOURTH FINDING IS GENUINELY CORRECT and must keep firing: T-1382 ("Decouple
frob from the Makefile") is 28d queued, is NOT decomposed, has no child carrying
it, and its message says plainly "it is rotting; work it, re-prioritize it, or
drop it". That is the shape TICK004 exists to catch. Whatever you change must
still fire on it.

WHAT TO BUILD:
  1. Exempt a ticket from TICK004's age trigger when it has at least one
     non-terminal child (the exact condition the rule already computes and
     prints). Do not add a second, separately-drifting definition of
     "decomposed" -- reuse the one that produces the existing message.
  2. Consider whether the age should instead be measured against the CHILDREN's
     progress -- an epic whose children are all also stalled IS rotting, and
     that is the finding worth having. If that is more than this ticket should
     carry, say so and file it, but say which you chose.
  3. Keep the informational signal. The current message's "the age is real and
     still worth noting" is true. A WARN or a note is defensible; an ERROR that
     can only be cleared by lying is not.

DO NOT fix this by raising the age threshold. That trades a false positive today
for the same false positive next month, and it weakens the rule against the case
it gets right.

DO NOT fix it by changing the three tickets. Their state is correct. The gate is
what is wrong, and editing healthy tickets to satisfy a bad rule is precisely the
failure mode this repo's own directives warn about.

MUST-FIRE FIXTURE: an aged, high-priority ticket with NO non-terminal child --
T-1382's exact shape -- still reports.
MUST-STAY-QUIET FIXTURE: an aged epic with a live non-terminal child does not
report as an ERROR.
THIRD FIXTURE: an aged epic whose children are ALL terminal (nothing actually in
flight) still reports -- decomposition that has stalled is real rot.

ACCEPTANCE
- The three epics stop erroring without any change to their own ledger state.
- T-1382 still fires.
- All three fixtures present.
- A stated decision on the children's-progress question.

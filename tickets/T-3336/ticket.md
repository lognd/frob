---
id: T-3336
title: frob ticket close reports success on a ticket land then refuses as NotCloseable,
  and done-report does not mirror like its sibling verbs
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_done_report.py
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
MEASURED 2026-08-28 landing T-3277. Two defects in the same seam, both found
because a land refused for a reason its own close had reported success for.

DEFECT 1: CLOSE AND LAND DISAGREE ABOUT WHAT "CLOSED" MEANS.

`frob ticket close` succeeded. Under the rapid profile's relaxed evidence rule
it reported success and moved the ticket to `done`. But it never produced the
one artifact `frob ticket land`'s NotCloseable check actually greps for: a
literal `## Done report` heading.

The subsequent land refused:

    ERROR: land: T-3277 cannot land -- missing evidence or a Done report
    ERROR: ticket land failed: NotCloseable

So a ticket can be `state: done` locally, with a close that reported success,
and still be structurally unlandable. The coordinator hit this independently
before the owning agent did -- I attempted the land, got the same refusal, and
could not tell from the ticket whether the agent had failed to write a report
or the gate was wrong.

CONTRIBUTING CAUSE, worth stating because it is its own trap: the agent wrote
its Done report through a body-append, deliberately AVOIDING the literal
"## Done report" heading, because the append tool refuses text containing that
heading as an ambiguous edit target. So one tool's safety check pushed the
content into a shape a second tool's gate cannot see. Neither tool is wrong on
its own terms.

DEFECT 2: `frob ticket done-report` DOES NOT MIRROR TO THE PRIMARY CHECKOUT.

`body`, `evidence` and `new` all mirror a worktree write back to the primary
checkout. `done-report` does not. The agent had to run it TWICE -- once in the
worktree so the land would see it, once directly against the root so main would
have it -- and that duplication then produced an add/add merge conflict on
`tickets/T-3277/done-report.md` when the two independently-generated copies
met, resolved by hand.

So the workaround for defect 2 manufactures a third problem.

WHY THIS MATTERS BEYOND ONE STUCK LAND. `close` reporting success while leaving
the ticket unlandable is the same shape as this project's dominant defect
class: an operation reports a state it has not actually achieved. It cost two
separate agents multiple attempts on one ticket, and neither could diagnose it
from the ticket's own contents. In a consumer repo, where the operator does not
have frob's source open in another window, this is a dead end.

WHAT TO BUILD:
  1. Make close and land agree. Either close PRODUCES what land requires, or
     close REFUSES with the same message land would give. Do not leave a state
     that one verb calls success and the next calls NotCloseable. State which
     direction you chose and why.
  2. `done-report` must mirror like its siblings, or must say plainly that it
     does not and what to run. Silent asymmetry between sibling verbs is the
     trap here -- the agent reasonably assumed it behaved like `body`.
  3. Resolve the heading collision at the root: one tool refuses text
     containing `## Done report` while another requires exactly that heading.
     Whatever the fix, those two rules must be made aware of each other rather
     than each being locally correct.

DO NOT FIX THIS BY LOOSENING LAND'S NotCloseable CHECK. Requiring a real Done
report before publishing is correct and is the guard that makes done-reports
trustworthy at all. The defect is that close does not produce what land
demands, not that land demands it.

MUST-FIRE FIXTURE: a ticket closed under the rapid profile without a Done
report is refused AT CLOSE TIME, with the same wording land would use.
MUST-STAY-QUIET FIXTURE: a normal close that produces a Done report lands
without extra steps.
THIRD FIXTURE: `done-report` written in a worktree is visible in the primary
checkout without a second manual invocation, and produces no add/add conflict.

ACCEPTANCE
- No state exists where close succeeds and land reports NotCloseable for the
  missing-report reason.
- `done-report`'s mirroring behaviour matches its siblings or is documented at
  the point of use.
- The heading collision between the append guard and the land gate is resolved.
- All three fixtures present.

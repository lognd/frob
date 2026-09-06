---
id: T-4068
title: ticket new prints 'created T-XXXX' before a rollback can occur, so a phantom
  id enters transcripts and citations
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_new.py
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
`frob ticket new` PRINTS "created T-XXXX" AND THEN ROLLS THE TICKET BACK, leaving
a success line in the transcript for a ticket that does not exist. Measured in
this repo, 2026-09-06, while filing a consumer finding:

    WARNING: tickets: new_ticket evidence [] recorded UNRESOLVED ...
    created T-4065: F-272: the TS walker rejects syntax vitest runs fine ...
    WARNING: ticket new: T-4065: scope overlaps T-1608 (queued) on: ...
    WARNING: ticket new: T-4065: scope overlaps T-1609 (queued) on: ...
    WARNING: ticket new: T-4065: scope overlaps T-3248 (queued) on: ...
    WARNING: ticket new: T-4065: scope overlaps T-4016 (queued) on: ...
    WARNING: tickets: refused -- a `frob ticket land` process (pid 423209) is
      running against this repository for T-4057 ...
    ERROR: ticket new: T-4065 could not be filed -- a land is in progress; the
      just-written ticket was ROLLED BACK (root is clean, no id was consumed)

`ls tickets/T-4065` -> No such file or directory. The ticket does not exist, and
the exit status was 1.

THE ROLLBACK ITSELF IS EXCELLENT AND MUST NOT CHANGE. It is atomic, it says
plainly what happened, it confirms the root is clean, it confirms no id was
consumed, and it tells the user exactly what to do ("retry this same command once
the land finishes"). That is a model failure message and it is the opposite of
the problems filed elsewhere today.

THE DEFECT IS SOLELY THE EARLIER "created" LINE. It is emitted BEFORE the
operation is durable, then contradicted five lines later. A reader who stops at
the first affirmative -- or greps for `^created`, which is the natural way to
capture the new id -- records a ticket that was never filed. I nearly did exactly
that: my filing command greps for `^created`, saw it, and only the non-zero exit
prompted me to read further.

WHY THIS IS MORE THAN COSMETIC. Coordinators and agents parse this output to learn
the allocated id, then reference it in later commands, in reports, and in other
tickets' cross-references. A phantom id propagates: it gets cited in bodies, in
Done reports, and in FROBLEMS follow-ups, and every one of those citations is
dangling. That is the same population this repo already tracks as dangling
T-draft citations (T-3893), created by a different mechanism.

THE FIX: do not announce creation until the write is durable. Emit the "created"
line AFTER the land-in-progress check and any other precondition that can trigger
a rollback -- or emit it only on the success path. The scope-overlap WARNINGs have
the same problem and should follow the same ordering; they name a ticket id that
may never exist.

CHECK FOR SIBLINGS: any verb that prints a success line before a late guard can
roll it back has this shape. `frob ticket new` is the one measured; grep the
mutation verbs (accept, scope, evidence, body, promote) for an announcement
emitted before the final durability check.

RELATED: T-4006 collects the inverse defect -- ERROR-labelled lines on outcomes
that SUCCEEDED. This is a SUCCESS-labelled line on an outcome that FAILED. Same
root property: output severity and ordering do not track the actual result. Worth
fixing with the same discipline, and worth noting on that ticket.

MUST-FIRE FIXTURE: a `ticket new` rolled back by a land-in-progress prints NO
"created" line.
MUST-STAY-QUIET: a successful `ticket new` still prints its created line and id.
THIRD FIXTURE: no scope-overlap warning names an id that is not durably created.

ACCEPTANCE
- The creation announcement moved after the last rollback-capable check.
- Sibling mutation verbs audited for the same premature-announcement shape.
- All three fixtures committed.
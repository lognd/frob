---
id: T-4021
title: 'F-233: a wrongly-dropped ticket cannot be reopened, so its history is split
  across two ids'
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-233, 2026-09-06:

  "T-0189 was dropped as folded into T-0169; T-0205 found the finding still
   present. `reopen` requires state=done, so the only path was a new ticket
   (T-0208) with the history split across two ids. Allow reopening a dropped
   ticket with a reason (the audit trail is the reason line)."

THE PREMISE THEY ARE CHALLENGING IS A DELIBERATE ONE, so engage with it rather
than treating this as an oversight. This repo established the rule that `fail`
requeues and DROP IS TERMINAL, and that distinction is load-bearing: it exists so
an agent cannot quietly resurrect scope that a human decided to cut. That is
worth preserving.

BUT TERMINAL IS NOT THE SAME AS INFALLIBLE, and that is the gap. Their drop was
made on a belief -- "folded into T-0169" -- that later turned out to be FALSE:
the finding was still present. Nothing about the terminality of drop is
justified when the reason for dropping was simply wrong. The current design
treats a mistaken drop and a considered drop identically, and offers no path back
from either.

THE COST IS NOT INCONVENIENCE, IT IS EVIDENCE LOSS. Re-filing produced T-0208
with "the history split across two ids". So the ticket that records WHY the work
was originally scoped, what was investigated, and what was believed when it was
dropped is severed from the ticket that actually does the work. Every downstream
consumer of ticket history -- triage, the audit trail, any future question of
"did we already look at this" -- now has to know both ids to reconstruct one
story. Terminality was meant to protect the record; here it fragmented it.

THEIR PROPOSED FIX IS THE RIGHT SHAPE and preserves the original intent: allow
reopen from dropped WITH A MANDATORY REASON. The reason line IS the audit trail,
and it makes the resurrection a deliberate, attributable act rather than a silent
one -- which is exactly what the terminality rule was protecting against. A drop
that can only be undone by writing down why is not a weakened rule.

WHAT TO DETERMINE FIRST: does anything downstream ASSUME dropped is terminal --
reporting, milestone accounting, the rot detector, archive handling? If a
consumer treats dropped as a closed set, reopening one could corrupt a count or
strand an archived artifact. Grep before implementing; this is a state-machine
change, not a flag.

BE CAREFUL WITH THE DEFAULT. Reopen-from-done and reopen-from-dropped are
different acts and should not silently share a code path or a message. A dropped
ticket has no done-report and may have no evidence; reopening it must land in a
state that reflects that, not in one that implies prior completion.

DISTINGUISH THIS FROM T-3998 (F-212), which is about a LEASE that cannot be
released without stealing the whole ticket. Both are "a state with no way out",
but the mechanisms and fixes are unrelated -- do not merge them.

MUST-FIRE FIXTURE: reopening a dropped ticket without a reason is refused.
MUST-STAY-QUIET: a dropped ticket stays dropped and out of the doable set until
someone explicitly reopens it -- the terminality guarantee survives.
THIRD FIXTURE: a reopened-from-dropped ticket lands in a state consistent with
having no done-report, and its drop reason plus reopen reason are both preserved.

ACCEPTANCE
- Reopen-from-dropped with a mandatory reason.
- Downstream assumptions about drop terminality identified before the change.
- The two reopen paths distinguished, not merged.
- All three fixtures committed.
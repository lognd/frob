---
id: T-4140
title: files frob writes on a ticket's behalf (filed drafts, done reports, mirrored
  transitions) count against that ticket's scope, so filing a follow-up penalises
  the agent that files it
state: queued
kind: bug
origin: agent
created: '2026-09-07'
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
acceptance:
- text: given an agent that files a follow-up ticket mid-work, when the filing ticket's
    scope is later checked, then the new ticket's files are not reported as out of
    scope
  evidence: []
- text: given an agent that hand-edits a ticket file outside its declared scope, when
    the scope gate runs, then SCOPE001 fires exactly as today
  evidence: []
- text: given a done report and a mirrored ledger transition written by frob, when
    the scope gate runs, then neither is reported against the ticket
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FILES FROB ITSELF WRITES ON A TICKET'S BEHALF ARE COUNTED AGAINST THAT TICKET'S
SCOPE. Reported twice by logand.app-v2, independently:

  F-316: "Every agent that files a follow-up sees SCOPE001 for the new ticket
         directory and has to either scope-add it or explain it away." Named on
         three of their tickets.
  F-342: filing auto-commits the new draft's file into the FILING ticket's
         worktree, and the scope gate then reports it as an out-of-scope touched
         file "for the rest of the ticket's life." Named on two more.

Five ticket instances across two reports. Their proposed rule is the same both
times and is correct: files frob writes on the ticket's behalf -- drafts it
filed, done reports, mirrored ledger transitions -- should be scope-exempt BY
CONSTRUCTION.

THIS HITS OUR OWN FLEET CONSTANTLY AND WE HAVE BEEN PAYING IT WITHOUT NAMING IT.
Filing a follow-up is the behaviour this project actively wants: an agent that
finds an unrelated defect mid-ticket should record it rather than silently widen
its diff. Today, doing the right thing adds a finding to your own ticket, and the
cheapest way to clear it is to widen scope to cover a file you did not choose to
write -- or to not file the follow-up at all. That is the wrong-incentive class
pointed directly at the queue's own health.

THE OBVIOUS FIX IS THE DANGEROUS ONE, AND THIS IS THE CENTRAL CONSTRAINT ON THIS
TICKET. Do NOT exempt "files under the ticket directory". Ticket files are
exactly what a great many tickets legitimately touch, and this repo has already
recorded an incident where an exemption written to match the normal case
disabled the guard entirely. An exemption that covers every path under the ledger
directory would silently stop the scope gate from ever policing ledger edits
again.

The exemption must key on PROVENANCE, not on path shape: this file was written by
frob, during this ticket, as a side effect of a verb the agent ran -- not by the
agent editing it. Those are different facts and only the first should be exempt.
Determine what the system already knows that can carry that distinction:
  - the ledger auto-commit path already knows it is the author at write time
  - the commits it makes are frob's own, with recognisable shapes
  - the ticket's own record already knows which drafts it filed
Pick a mechanism that cannot be spoofed by an agent hand-editing the same file,
and say why the one you picked has that property. If no such fact exists today,
recording it is part of this ticket.

SCOPE THE POPULATION BEFORE FIXING. The reporters name three kinds -- filed
drafts, done reports, mirrored ledger transitions. Enumerate every file frob
writes on a ticket's behalf, because a fix covering the three they hit will be
reported a third time by whoever hits the fourth. Report the list.

MUST-FIRE FIXTURE:   an agent files a follow-up ticket mid-work; the filing
                     ticket's later scope checks do not report the new ticket's
                     files.
MUST-STAY-QUIET:     an agent HAND-EDITS a ticket file outside its declared
                     scope and SCOPE001 still fires exactly as today -- the
                     exemption must not become a blanket ledger escape.
THIRD FIXTURE:       a done report and a mirrored ledger transition written by
                     frob are likewise exempt, proving the fix covers the
                     enumerated population and not just the one reported case.

ACCEPTANCE
- The exemption keys on provenance, not on path prefix, with the chosen
  mechanism's spoof-resistance stated.
- The full population of frob-written-on-behalf files enumerated and reported.
- The hand-edit case proven still caught.
- All three fixtures committed.

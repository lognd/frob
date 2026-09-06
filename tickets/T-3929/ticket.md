---
id: T-3929
title: 'promoting a draft renames the ticket but not its inbound citations: 243 dangling
  draft ids measured on main'
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
PROMOTING A DRAFT RENAMES THE TICKET BUT NOT THE CITATIONS THAT POINT AT IT.
Reported as logand.app-v2 F-157: "T-0063's WIRE001/WIRE002 waivers cited
T-draft-a75dadd0; after promotion the waivers still cite the dead id."

SCALE, MEASURED IN THIS REPO 2026-09-05:

    distinct T-draft-* ids cited under tickets/ :  243
    of those, many have NO surviving ticket directory

I measured the 243 while checking whether today's agent-filed drafts had
survived a land (they had -- every one reached a real id). The dangling
population is therefore NOT lost work; it is CITATION ROT, and F-157 names the
mechanism that produces it: the promote path renames the ticket and leaves every
inbound reference pointing at an id that no longer resolves.

WHY THIS IS MORE THAN UNTIDY, and the reason it deserves priority over its
cosmetic appearance:

  1. A WAIVER WHOSE follow_up CITES A DEAD ID MAY NOT DISCHARGE. WIRE002
     requires a WIRE001 waiver to "bind to a real, open follow-up ticket". If
     promotion kills the citation, that waiver is either permanently in
     violation or -- worse -- silently satisfied by a reference to nothing.
     DETERMINE WHICH: a rule that passes against a dead pointer is a hole; a
     rule that fails against one is friction. They need different fixes and the
     consumer's report does not distinguish them.
  2. IT DESTROYS TRACEABILITY AT EXACTLY THE MOMENT WORK BECOMES REAL. The
     citation is written while the work is a draft; it breaks when the draft is
     promoted -- i.e. when someone decided the work matters enough to give it a
     number.
  3. IT MAKES A MISSING DRAFT ID AMBIGUOUS. Combined with the consumer's
     separate report that drafts filed inside a worktree sometimes do not
     survive a land, a dead T-draft citation could mean "promoted, citation
     stale" or "lost in a land". Today's check says survival happened, but the
     two causes are indistinguishable from the citation alone.

WHAT TO BUILD:
  a. RETARGET INBOUND CITATIONS AT PROMOTE TIME. The promote path knows both
     ids at the moment it renames -- that is the cheapest possible place to fix
     the references, and it prevents recurrence rather than cleaning up after.
  b. RECORD THE MAPPING DURABLY. Even with (a), historical citations exist and
     some live in ARCHIVED done-reports that must not be rewritten (this repo
     established that landed done-reports are historical artifacts). A
     draft->real mapping that resolution can consult makes those readable
     without editing them.
  c. A RULE FOR A CITATION TO A DRAFT ID THAT IS NEITHER LIVE NOR RESOLVABLE
     THROUGH THE MAPPING. Without it the population re-accrues.

DO NOT BULK-REWRITE THE 243 BY REGEX. Some are legitimately live in-flight
drafts; some sit in archived done-reports that are historical records; a blanket
substitution would corrupt both. Separate the populations FIRST and report the
counts -- live drafts, promoted-and-dangling, archived-historical -- before
touching anything. The number that matters is the second one, and it is not
243.

MUST-FIRE FIXTURE:   a citation to a promoted draft id that has no mapping entry
                     is flagged.
MUST-STAY-QUIET:     a citation to a genuinely live in-flight draft is not.
THIRD FIXTURE:       promoting a draft leaves NO dangling inbound citation.

ACCEPTANCE
- The three populations counted separately.
- The WIRE002-against-a-dead-id question answered (hole or friction).
- Retargeting at promote time, plus a durable mapping for history.
- Archived done-reports left unedited, with that policy stated rather than
  assumed.
- All three fixtures committed.

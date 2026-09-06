---
id: T-4101
title: promoting or closing a draft leaves every citation of the old id dangling (246
  measured, three consumer reports, all fixed by hand)
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
PROMOTING OR CLOSING A DRAFT RENAMES THE TICKET AND LEAVES EVERY CITATION OF THE
OLD ID DANGLING. Reported three times by the same consumer and never filed until
now -- that omission is mine, and it is why the third report exists.

THE THREE REPORTS:
  F-157  "T-0063's WIRE001/WIRE002 waivers cited T-draft-a75dadd0; after promotion
          the waivers still cite the dead id."
  F-294  "`frob ticket close` renumbered the draft follow-up to T-0259 but LEFT
          THREE PROSE CITATIONS of the draft id (docstrings, decision doc)
          unrewritten; the agent fixed them by hand."
  F-302  "T-0247: THREE CITATIONS (a doc-table cell and two source comments) still
          named T-draft-... after promotion to T-0269; fixed by hand. The
          promotion should rewrite every tracked-file occurrence of the draft id."

MEASURED IN THIS REPO, 2026-09-06:

    distinct T-draft-* ids cited under tickets/ : 246
    of those with no surviving ticket directory : 246

EVERY ONE IS DANGLING. That is not proof of 246 defects -- see the caution below --
but it is the population this defect produces, and it is growing.

THE MECHANISM IS SIMPLE AND THE FIX POINT IS OBVIOUS: the promote/close path knows
BOTH ids at the moment it renames. That is the cheapest possible place to retarget
inbound references, and it prevents recurrence rather than cleaning up afterwards.

WHY IT IS MORE THAN UNTIDY:
  1. A WAIVER WHOSE follow_up CITES A DEAD ID MAY NOT DISCHARGE. WIRE002 requires
     a WIRE001 waiver to bind to a real, open follow-up ticket. If promotion kills
     the citation, that waiver is either permanently in violation or -- worse --
     SILENTLY SATISFIED BY A REFERENCE TO NOTHING. DETERMINE WHICH: a rule that
     passes against a dead pointer is a hole; one that fails is friction. They
     need different fixes and no report distinguishes them.
  2. IT BREAKS TRACEABILITY EXACTLY WHEN THE WORK BECOMES REAL. The citation is
     written while the work is a draft and breaks at promotion -- i.e. when
     someone decided it mattered enough to give it a number.
  3. THE ONLY REMEDY TODAY IS HAND-EDITING. Both later reports end "fixed by
     hand", and this repo's standing rule is that the ledger must never be
     hand-edited. So the defect forces the operation the rules forbid -- the same
     shape as T-3958's hand-copied ticket files.

DO NOT BULK-REWRITE THE 246 BY REGEX. Three populations are mixed together and
only one is the target:
  (a) legitimately LIVE in-flight drafts,
  (b) promoted-and-dangling -- the actual defect,
  (c) ARCHIVED done-reports, which are historical records this repo has
      established must not be rewritten.
SEPARATE AND COUNT THEM FIRST and report the three numbers. The number that
matters is (b), and it is not 246.

CAUTION ON THE MEASUREMENT ITSELF: T-4015 records that ticket-id matching has no
token boundary (UT-2207 reads as T-2207). My count above greps the unambiguous
`T-draft-[0-9a-f]+` shape so it should not be inflated by that -- but re-measure
after T-4015 lands rather than trusting a number taken before it.

MUST-FIRE FIXTURE: a citation to a promoted draft id that has no mapping entry is
flagged.
MUST-STAY-QUIET: a citation to a genuinely live in-flight draft is not.
THIRD FIXTURE: promoting a draft leaves NO dangling inbound citation in tracked
files.
FOURTH FIXTURE: archived done-reports are not rewritten.

ACCEPTANCE
- The three populations counted separately and reported.
- The WIRE002-against-a-dead-id question answered (hole or friction).
- Retargeting at promote/close time, plus a durable draft->real mapping for
  history that must not be edited.
- All four fixtures committed.
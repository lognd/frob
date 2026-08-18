---
id: T-2400
title: TICK006 auto-files false phantom-citation tickets for ids that exist on main
  but postdate the worktree
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given a Done report citing a ticket that exists on main but was filed after
    the landing worktree was cut, when the land's TICK006 check runs, then it files
    no recovery ticket.
  evidence: []
- text: Given a Done report citing a genuinely nonexistent ticket id, when the same
    check runs, then it still files a recovery ticket, proving the fix did not simply
    disable the check.
  evidence: []
- text: Given the check cannot read the merge target's ledger, when it runs, then
    it reports NOT_MEASURED with a reason rather than concluding the citation is phantom.
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
TWICE TODAY, a Tier-A `TICK006` auto-fix during land filed spurious
"phantom citation recovery" tickets for ticket ids that GENUINELY EXIST
on main, forcing the landing agent to hand-drop them:

  - Series U's land of T-2341 auto-filed T-2382/T-2383 citing T-2366 and
    T-2367. Both cited tickets were real (`frob ticket show` confirmed);
    the agent verified and dropped the two spurious ones.
  - Series Y's land of T-2386 auto-filed T-2398/T-2399 citing T-2388 and
    T-2389. Both cited tickets were real, filed BEFORE the worktree was
    cut; the agent verified and dropped both.

MECHANISM (from the second occurrence, which pins it down). The Done
report cites ticket ids that exist on MAIN but were created after the
agent's WORKTREE was cut. The phantom check evidently resolves the
citation against the worktree's own view of the ledger rather than
against main, so a ticket filed by the coordinator or a sibling agent
mid-flight looks nonexistent from inside the worktree. It is not a
missing ticket -- it is a stale view of the ticket set.

This is the same root cause class as T-2350/T-2351 (already fixed for a
different shape) and belongs to the family of auto-filer defects that
have now produced FOUR distinct kinds of malformed record: absolute
paths in a scope field (T-2342, which bricked `frob ticket new`
fleet-wide), identity-less quarantine findings (T-2207), stale-baseline
"new" identities (pre-existing findings filed as new), and now
false-phantom citations.

COST. Each occurrence burns two ticket ids, forces the landing agent
into a verify-then-drop detour at the most expensive moment (mid-land),
and -- worse -- trains agents to treat auto-filed tickets as
presumptively bogus. A recovery mechanism that cries wolf is worse than
none, because the one time it is right it will also be dropped. Drops
are TERMINAL in this repo (no undrop), so a false-positive filer is one
careless agent away from destroying a real finding.

FIX SHAPE. Resolve a cited ticket id against the ledger as it exists on
the MERGE TARGET (main), not the worktree's snapshot -- the citation is
being checked for a land onto main, so main is the correct reference.
Where that is genuinely unavailable, the check must report NOT_MEASURED
rather than concluding "phantom" (epic T-2391): concluding absence from
an incomplete view is precisely the silent-wrong-answer class that
doctrine exists to eliminate. Filing a recovery ticket must be the
action of LAST resort, taken only when the id is provably absent from
the merge target.

Positive control both ways is mandatory here, because a lazy fix
(suppress phantom filing entirely) would pass a one-sided test:
  - must-still-fire: a Done report citing a genuinely nonexistent
    ticket id must still produce a recovery filing;
  - must-now-be-silent: a Done report citing a ticket that exists on
    main but postdates the worktree's cut must file nothing.

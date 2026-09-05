---
id: T-3899
title: TICK014 inspects only the close commit, so it flags every ticket following
  the one-logical-change-per-commit convention
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
Reported as typani FROBLEMS T-023. TICK014's premise contradicts the commit
discipline this project mandates, so the rule fires on the NORMAL workflow.

THE REPORT:

    13 TICK014 warnings ("closed done with a diff touching only ticket
    bookkeeping") for tickets whose work was committed in a `feat:`/`fix:`
    commit and then closed in a following `chore(tickets): close T-####`
    commit. The check looks only at the close transition's own commit.

So TICK014 asks "did the close commit contain real code?" -- and the answer is
NO for every ticket that follows the standing convention "commit incrementally:
one logical change per commit, not one giant commit at the end". frob's own
ledger commits are literally named `chore(tickets): ...`, which is that
convention applied to bookkeeping.

THE RULE AND THE CONVENTION CANNOT BOTH BE RIGHT. Either the close must be
committed together with the code -- which contradicts one-logical-change-per-
commit and would produce mixed `feat:`+`chore(tickets):` commits -- or the check
is looking at the wrong diff. It is the latter.

WHY THIS MATTERS HERE AND NOT ONLY IN typani: FROB'S OWN COUNT IS 883. TICK014
is the second-largest warning family in this repo (behind CPLACE002's 1270), and
T-3863 was just filed as its burn-down ticket with 883 as the denominator. IF
THIS DIAGNOSIS IS RIGHT, MOST OF THAT 883 IS NOT DEBT TO BURN DOWN -- IT IS ONE
RULE DEFECT, AND T-3863's PREMISE IS WRONG.

MEASURE THAT FIRST, before any work on either ticket. Sample 20 of frob's own
TICK014 findings and classify each: (a) the ticket's code genuinely landed in a
separate commit from its close -- false positive, this defect; (b) the ticket
genuinely closed with no code anywhere in its lifetime -- true positive, real
debt. Report the split. That ratio decides whether T-3863 is a burn-down at all
or should be closed as absorbed by this ticket.

THE FIX, per the reporter and it is the obvious one: consider the ticket's
LIFETIME diff -- start transition commit through close commit -- rather than the
close transition's own commit. frob already knows both commits; the start
transition is recorded (`chore(tickets): record T-#### start transition`) and
the close is the one being checked.

CHECK THE EDGE CASES before implementing, because a lifetime diff is broader
and could mask what TICK014 legitimately catches:
  - a ticket that landed code, then had it reverted before close
  - a ticket whose lifetime spans another ticket's commits (concurrent work on
    the same branch) -- does the lifetime diff wrongly credit someone else's
    code?
  - a ticket closed without ever starting (no start transition to bound the
    range)
State how each is handled. The rule exists to catch a ticket closed `done` with
nothing behind it, and that guard must survive.

ALSO FIX THE REMEDY. The reporter notes the suggested `--declare-no-scope`
remedy is WRONG for these cases: "the work landed". A remedy that tells you to
declare no scope when you did in fact ship code is actively misleading, and this
is the second remedy-string defect found this week (T-3859: MILE003 names a
flag the verb does not accept). Cross-reference it.

MUST-FIRE FIXTURE:   a ticket closed with NO code in its entire lifetime is
                     still flagged
MUST-STAY-QUIET:     a ticket whose code landed in a `feat:` commit and closed
                     in a following `chore(tickets):` commit is not flagged
THIRD FIXTURE:       a ticket whose code landed and was then reverted before
                     close is still flagged (or explicitly decided otherwise)

ACCEPTANCE
- The 20-sample classification of frob's own 883 reported, with the split.
- T-3863 re-scoped or closed as absorbed, based on that number.
- Lifetime-diff implementation with the three edge cases decided in writing.
- The remedy string corrected.
- All fixtures committed.

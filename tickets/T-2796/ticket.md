---
id: T-2796
title: a large fraction of the queued backlog is already resolved by landed work,
  and 'already resolved' was being requeued instead of dropped
state: queued
kind: feature
origin: agent
created: '2026-08-21'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/investigations/
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
## Measured

Of the tickets worked in one night's drain, EIGHT were found to be already
resolved by previously-landed work, plus four of the six sub-cases inside
T-2686:

    T-2589  already in gates.md + _KNOWN_GATE_RULES     -> dropped (T-2372)
    T-2600  already split by T-2614                     -> dropped (T-2614)
    T-2558  citation already retired by T-2565          -> dropped (T-2565)
    T-2548  already fixed by T-2678                     -> dropped (T-2678)
    T-2754  ARCH103 already resolved by T-2738/T-2749   -> dropped
    T-2692  ratchet already raised by T-2407            -> dropped (T-2407)
    T-2686  4 of 6 cited node ids already rebound       -> no action needed
    T-2384  ~90% of the epic already done, unparented   -> 2 residue tickets

Against a queued backlog of 64, that is a large fraction of dispatched work
spent re-measuring things that were already finished. Every instance costs a
full agent dispatch, a worktree, and at least one `frob check`.

## Two distinct causes, and they need different fixes

1. WORK LANDS WITHOUT CLOSING THE TICKETS IT RESOLVES. A fix that
   incidentally resolves three other open tickets closes one. Nothing
   notices the other two. T-2384 is the extreme case: ~90% of an epic was
   completed by tickets filed with `parent: null`, so the epic read as
   undecomposed with zero children while nearly finished.

2. "ALREADY RESOLVED" WAS BEING REQUEUED, NOT DROPPED. Agents were
   instructed (by me) to run `frob ticket fail` with the measurement
   recorded when they found a ticket already satisfied. But `fail`
   REQUEUES. So the verdict returns the ticket to the pool for the next
   agent to rediscover and re-measure at full cost. T-2692 sat in exactly
   that state until dropped by hand.

   The correct dispositions, which should be documented and enforced:
   - already resolved by landed work -> `frob ticket drop --absorbed-by <id>`
     (terminal, names the survivor, preserves the measurement)
   - blocker still genuinely real     -> `frob ticket fail` (requeue is right)
   These are different verdicts and must not share a verb.

## What to build

The first deliverable is a MEASUREMENT of the whole queued backlog, not a
patch: for each of the 64 queued tickets, does its stated defect still
reproduce on current main?

Then propose the durable mechanism. Candidates, to be chosen on evidence:
- a `frob ticket` query that re-measures a ticket's own claim and reports
  reproduces / does-not-reproduce / cannot-measure. Note the third state is
  mandatory -- "cannot measure" must never render as "does not reproduce",
  which is this repo's dominant bug class (epic T-2391).
- a land-time check: when a land resolves a gate finding identity that ANY
  other open ticket also names, surface those tickets. T-2760 already added
  a structured `findings: tuple[tuple[str,str], ...]` field and a
  `--finding RULE:FILE` flag for exactly this kind of identity matching --
  reuse it, do not invent a second mechanism.

## Constraints

- Do NOT auto-drop on a re-measurement. Auto-drop has already false-dropped
  live findings in this repo on a path-shape mismatch, and a drop is
  TERMINAL (there is no undrop). Report candidates for a human/coordinator
  decision; at most, propose.
- A ticket whose finding does not reproduce is NOT automatically resolved --
  it may be unmeasurable, or the detector may have been narrowed. Require a
  named survivor (the landed ticket that fixed it) before proposing a drop,
  exactly as the six manual drops above did.
- Positive controls both directions: a ticket whose defect genuinely still
  reproduces must be reported as LIVE; a ticket already fixed by a known
  landed ticket must be reported as resolved WITH that ticket named.

## Note

`frob ticket doable` now runs in 12s (T-2629) and already reports HOT FILE
contention per ticket, so it is the natural surface for this if a query is
the answer. Do not build a parallel listing.

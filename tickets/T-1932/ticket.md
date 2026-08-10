---
id: T-1932
title: 'Structural: land runs mutations AFTER the guards that gate them, so any guard''s
  decision can be silently invalidated'
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
THIS IS THE GENERAL CASE BEHIND AT LEAST THREE SEPARATE BUGS. Each was
filed and fixed as a one-off; the ordering defect that produced all three
has never been addressed, so the next guard added to the land path
inherits the same hazard by default.

THE INVARIANT THAT IS VIOLATED: on the land path, no mutation may run
after a guard whose decision that mutation can invalidate. Today land
does exactly that -- it absorbs `frob fmt` and the T-1138 Tier-A
deterministic auto-fix handlers, which REWRITE FILES, and various guards
run before that rewriting.

THE THREE MEASURED INSTANCES:

1. T-1903 (done) -- "Pre-land strata parse guard runs BEFORE the Tier-A
   rewrite, so it cannot catch corruption the rewrite itself introduces."
   Recorded consequence: three lands published an unparseable self-model
   while reporting LAND-PROOF verified=True.

2. T-1910 / T-1920 (done) -- the ticket close and REL001 bump ride the
   SAME commit the ancestry check runs against, so by the time
   verified=False is observable the terminal state and version bump are
   already written. T-1920 had to fix this BY CONSTRUCTION (check
   reachability before the terminal write) precisely because no
   after-the-fact guard could work.

3. T-1931 (queued, observed live during T-1556 s land at 16880d5170a2) --
   the CrossTicketLeakage guard correctly REFUSED a land touching
   design/frob.strata (T-1901 s declared scope). The offending line was
   reverted in the worktree, and land s own Tier-A auto-fixer then
   silently RE-ADDED it before the next attempt, so it landed anyway.
   A guard that refused was overruled by a mutation running after it.

Same shape three times: guard decides, mutation runs, decision is stale,
nobody re-checks. T-1931 is the worst variant because the guard did fire
and was simply overridden.

WHY A FOURTH POINT FIX IS NOT THE ANSWER. Fixing T-1931 alone leaves the
ordering unconstrained, so guard number four added next month repeats
this. The repo already has the lesson written down (a guard that runs
after the mutation it is meant to gate cannot prevent it, only report
it) and it keeps recurring anyway -- which means a written rule is not
sufficient and this needs to be enforced by construction.

FIX DIRECTION -- investigate and choose, with reasoning recorded:
(a) Re-run every guard after the LAST mutating step, so no decision can
    be stale. Simplest to reason about; cost is a second guard pass.
(b) Move all mutation strictly BEFORE all guards, so guards see final
    bytes. Cleanest ordering; requires the auto-fixers not to depend on
    guard output.
(c) Make the ordering explicit and machine-checked: declare each land
    step as mutating or gating, and add a test asserting no gating step
    precedes a mutating step it can be invalidated by.
(a) or (b) plus (c) is likely right -- (c) alone documents the invariant,
it does not establish it.

DO NOT resolve this by removing guards or by disabling land s auto-fix
absorption. Both are load-bearing. The deliverable is ordering, not
subtraction.

ACCEPTANCE
1. The land path has a single documented, enforced ordering between
   mutating steps and gating steps.
2. A test proves a guard s refusal cannot be undone by a later mutating
   step -- model it directly on T-1931 s live repro (guard refuses on a
   cross-ticket file, auto-fix re-adds it, land must still refuse). It
   must FAIL before the fix.
3. A test proves a mutation cannot introduce a defect that an
   already-run guard would have caught -- model on T-1903 (Tier-A rewrite
   corrupts design/frob.strata after the parse guard ran).
4. Adding a NEW guard or a NEW auto-fix handler to the land path cannot
   silently violate the ordering; state how that is prevented.

SEQUENCING: T-1931 may land first as the urgent point fix, or be folded
in here -- decide and say which. Do not let both land redundant
overlapping fixes to the same code.

Note src/frob/tickets/_land.py is high-traffic and every agent depends on
it. A regression here blocks the whole repo, as T-1882 demonstrated
earlier today. State explicitly what this change does under concurrent
lands.
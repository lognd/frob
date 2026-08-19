---
id: T-2564
title: a land killed between stage and commit leaves content in the shared index where
  another land can absorb it
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: placeholder; already narrow-scoped to src/frob/tickets/_land.py
  per ticket body, confirming with real narrowing
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OBSERVED 2026-08-18 by the agent landing T-2539, reported rather than
worked around.

A `frob ticket land` was SIGTERM'd at the 540s wrapper cap AFTER it had
staged the entire changeset into the SHARED ROOT's git index, but BEFORE
it committed. The staged content then sat in the shared index. Within
about a minute a concurrent process cleared it -- `git status` went from
10 staged paths to "working tree clean" -- with none of that content
reaching main.

Nothing was lost in this instance: the worktree branch still held the
work and a re-land succeeded. The hazard is the WINDOW, not this
outcome.

WHY THIS IS A DISTINCT VARIANT worth its own ticket: the known
staged-content hazard in the playbook (section 1b2) involves a stash.
This reached the same dangerous state with NO STASH INVOLVED -- purely
a killed land between stage and commit. So a reader who has internalized
the stash-shaped warning will not recognize this one.

THE RISK, stated precisely: between stage and commit, an unrelated
concurrent land committing in the shared root would sweep the abandoned
staged content into ITS OWN commit. That is the cross-ticket-leakage
class arriving through a route the CrossTicketLeakage guard does not
watch, because the guard reasons about a ticket's declared scope versus
its worktree diff, not about pre-existing index state in the root.

Note the interaction with the 540s wrapper cap: this is not a rare
crash. The fleet routinely hits that cap -- three instances in two
series on 2026-08-18 alone, all exit 143. Any land that stages before it
is killed lands in this window, so frequency scales with contention.

DELIVERABLE -- investigate before choosing:
1. Establish whether `land` can stage-and-commit atomically, or defer
   staging until immediately before the commit, so the window shrinks
   toward zero.
2. If a window is unavoidable, make it RECOVERABLE: a land that is
   killed mid-stage should leave a marker the next land can detect and
   refuse on (or reconcile), rather than leaving anonymous staged
   content that looks like ordinary dirt.
3. At minimum, a land must never COMMIT index content it did not itself
   stage. Verify what the current pre-commit path actually does here --
   if it commits `git diff --cached` wholesale, that is the leak.

Deliverable 3 is the one that matters most even if 1 and 2 prove
expensive: it converts "someone else's work silently joins my commit"
into "my commit contains only mine".

MEASURE FIRST, then fix. Reproduce the window deliberately (stage a
changeset in a scratch clone, kill the process between stage and commit,
run a second land) and confirm the sweep actually happens before
designing around it. It is possible some existing guard already prevents
the cross-contamination and only the abandoned-dirt symptom is real --
that would be a valuable clean negative and should be reported as such.

POSITIVE CONTROLS, BOTH DIRECTIONS:
- a land killed between stage and commit must not have its content
  absorbed by the next unrelated land;
- a normal, uninterrupted land must be completely unaffected -- no extra
  refusals, no added latency on the common path.

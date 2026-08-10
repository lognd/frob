---
id: T-1915
title: frob ticket doable lists permanent anchor tickets, so every dispatch wave re-assigns
  unworkable work
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-09. A dispatch wave of 5 agents assigned T-1820, T-1831,
and T-1778 to an implementer. All three are permanent WIRE001 follow_up
anchor tickets (T-1856 precedent): they exist solely to give a
frob:waive WIRE001 directive a live, non-terminal follow_up target, and
they must NEVER reach done or dropped, because WIRE002 disqualifies a
terminal follow_up target and closing one re-trips WIRE002 on main.

There is no work to do on them. There never will be. Yet they sit at the
top of `frob ticket doable` permanently, because `_doable.py` does not
filter on the anchor field at all -- grep for "anchor" in
src/frob/tickets/_doable.py returns only docs-anchor comments (COV007),
not a single read of the ticket anchor attribute.

COST, ALREADY PAID TWICE. T-1820 carries a recorded "2026-08-08 attempt
1" from a prior wave. This wave burned a second full agent slot
rediscovering the same conclusion. Under standing dispatch policy
(coordinator pops the top of `doable` and hands each agent a group), a
permanent anchor is not merely noise -- it is GUARANTEED to be
re-dispatched in every future wave, forever, and the agent must redo the
whole worktree warm-up before it can discover the ticket is a no-op.

T-1778 also documents the deeper wart: recording a fail attempt is "the
only existing mechanism land() has to publish a non-terminal ledger
record" for an anchor. So an anchor whose work IS complete has no honest
way to say so -- it must masquerade as a failure.

ACCEPTANCE
1. `frob ticket doable` does not list a ticket whose anchor field is
   set; anchors remain visible via `frob ticket list` and are NOT
   closed, dropped, or otherwise moved toward a terminal state.
2. There is a first-class way to record "this anchor is verified correct
   as of <sha>" without recording a fail attempt and without a terminal
   state transition.
3. A test proves an anchor ticket is excluded from doable while
   remaining queued and lease-eligible; it must fail before the fix.

CAUTION: do not implement 1 by closing anchors or by adding a blanket
exclusion for the docs kind -- both break WIRE002. The filter must key
on the anchor field itself.
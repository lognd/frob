---
id: T-4054
title: 'F-255: a refactor breaks doc anchors in a file another ticket owns, so the
  ticket that caused the drift cannot repair it'
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
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'F-267 sharpens this ticket: the same undischargeable doc obligation fires
    with NO refactor and no contract change (a one-token attribute edit), and its
    escape hatch is worse -- a permanent frob:waive comment in production source for
    a non-event. Raises the real question of what counts as a doc-affecting change'
  actor: logan
  at: '2026-09-06'
  old_length: 4315
  new_length: 7068
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2 F-255, 2026-09-06:

  "gate:DRIFT/gate:AFFECT flag docs/spec/L5-component-design/SUB-18-auth-pages.md's
   #comp-1802/1803/1804 frob:describes anchors as no-longer-resolving, since
   T-0230 moved TurnstileWidget/Claim/ResetPassword out of Register.tsx/
   VerifyEmail.tsx/ForgotPassword.tsx. FIXING THE ANCHOR TARGET PATH MEANS
   EDITING THAT DOC FILE, WHICH IS T-0052's DECLARED SCOPE, NOT T-0230's."

A REFACTOR CREATES AN OBLIGATION THE REFACTORING TICKET CANNOT DISCHARGE. Moving
a symbol is a legitimate, complete piece of work. It invalidates doc anchors
pointing at the old location -- correctly detected, that is what DRIFT/AFFECT are
for. But the anchors live in a file another ticket owns, so the ticket that
CAUSED the breakage is structurally barred from repairing it. The finding is
true, the fix is known and mechanical, and the person holding the fix cannot
apply it.

THIS IS A KNOWN SHAPE IN THIS REPO, now reported from outside it: moving symbols
breaks doc/test/waiver edges OUTSIDE the ticket's scope. What F-255 adds is the
LEASE dimension -- it is not merely that the edges are out of scope, it is that
they belong to a DIFFERENT LIVE TICKET, so widening scope is not available
either. Their resolution was to ack body/sig/doc facets with a reason and leave
the anchor path for "T-0052 (or a coordinator) to update once both land" --
i.e. a human holds the obligation in their head across two tickets.

WHY AN ACK IS THE WRONG PERMANENT ANSWER, even though it was the right move here:
an ack says "I re-verified the doc is still true". For a MOVED symbol the doc is
NOT still true -- the anchor points at a path that no longer contains it. So the
mechanism they were forced to use records a statement that is false, because the
mechanism that fits (update the anchor) was unreachable. A tool that leaves only
an inaccurate escape hatch will get inaccurate records.

WHAT TO BUILD -- and the first question decides the shape:
  DOES A CROSS-TICKET OBLIGATION EXIST AT ALL TODAY? A ticket needs a way to say
  "my change creates work in a file I do not own, here is what must happen, and
  here is the ticket that owns it". If that construct exists (a follow_up, a
  filed child, frob:pending per T-3977), the fix may be to route
  DRIFT/AFFECT-from-a-move into it automatically. If it does not, that construct
  IS the deliverable.

CANDIDATES, in preference order:
  1. AUTO-FILE THE REPAIR against the owning ticket, or as a follow-up blocked on
     both. The mover knows the old path, the new path, and which file holds the
     stale anchor -- everything needed to describe the work precisely.
  2. LET THE MOVE UPDATE THE ANCHOR PATH, treating a pure path retarget as
     mechanical rather than semantic, and exempt it from the owning ticket's
     lease. Narrow and appealing, but VERIFY it is truly mechanical -- an anchor
     move that also changes what the doc SAYS is not.
  3. Failing both, at minimum the finding should NAME the owning ticket so the
     obligation is visible rather than living in a human's memory.
(3) is the floor and should ship regardless.

RELATED, ALL CONFIRMED, ALL DISTINCT -- do not merge:
  T-3949  whole-file leases serialise disjoint edits (the LEASE granularity)
  T-4004  scope breadth pulls in files the ticket never touched (the DENOMINATOR)
  T-4050  the parent epic asking what set a ticket is accountable for
This is a fourth thing: work that legitimately BELONGS to one ticket and can only
be performed by another. Granularity and denominator fixes do not resolve it,
because even a perfectly-scoped ticket cannot edit another ticket's file.

MUST-FIRE FIXTURE: moving a symbol whose doc anchor lives in an out-of-scope file
produces an actionable obligation naming the file, the stale anchor, and the
owning ticket.
MUST-STAY-QUIET: a move whose doc anchors are all in-scope is repaired inline
with no extra ticket.
THIRD FIXTURE: an ack is not required to record a statement that is false -- a
moved symbol's stale anchor has a remedy other than acking that the doc is still
true.

ACCEPTANCE
- Whether a cross-ticket obligation construct exists, answered by grep first.
- Findings from a move name the owning ticket at minimum.
- The false-ack path removed, not merely discouraged.
- All three fixtures committed.
## F-267: THE SAME TRAP WITH NO REFACTOR AT ALL, AND A DIFFERENT WRONG INCENTIVE

logand.app-v2, 2026-09-06:

  "T-0235 changed `inert={true}` to `inert=""` in ImageCarousel.tsx; AFFECT001
   demanded the SUB-16 COMP-1605 doc be touched/acked, but THAT DOC WAS NOT IN
   THE TICKET'S SCOPE (correctly: NO CONTRACT CHANGED), so the agent had to add a
   `frob:waive AFFECT001` COMMENT TO THE SOURCE. A doc-drift gate that fires on a
   change with no signature or behaviour delta is noise, and PUSHING WAIVE
   COMMENTS INTO SOURCE for it is the wrong incentive."

THIS SHARPENS THIS TICKET IN TWO WAYS.

1. THE TRIGGER DOES NOT REQUIRE A REFACTOR. The case above involves symbols
   MOVING between files -- a substantial change with a genuine doc consequence,
   just one the ticket could not discharge. Here NOTHING MOVED and no contract
   changed: a JSX attribute's value went from `{true}` to `""`. The doc is still
   entirely accurate. So the gate is not detecting real drift and failing to let
   the ticket fix it; IT IS DETECTING NO DRIFT AT ALL and demanding an
   acknowledgement anyway. Any fix must distinguish "the doc is now wrong and you
   cannot reach it" from "the doc is still right and nothing is required".

2. THE ESCAPE HATCH IS WORSE HERE THAN IN THE REFACTOR CASE. Above, the agent
   acked -- recording a statement ("I re-verified the doc is still true") that
   was FALSE for a moved symbol. Here the agent had to write a
   `frob:waive AFFECT001` COMMENT INTO PRODUCTION SOURCE, permanently, for a
   one-token change. The consumer's phrasing is exactly right: that is the wrong
   incentive. A waiver in source is a durable artifact that outlives the ticket,
   the reviewer and the reason; accumulating them for non-events degrades every
   real waiver's signal.

SO THE UNDERLYING QUESTION IS SHARPER THAN "who may edit the doc": WHAT COUNTS AS
A CHANGE THAT CAN AFFECT DOCUMENTATION? A signature change, a behaviour change,
a moved symbol -- plausibly yes. A literal-value edit within one attribute, with
identical types and identical behaviour -- plausibly no. AFFECT001 currently
appears to key on the symbol being TOUCHED rather than on anything about the
change. VERIFY THAT before designing: if it is touch-based, the fix may be to key
on a meaningful delta (signature, exported surface, docstring text) rather than
on the diff mentioning the symbol at all.

DO NOT solve this by making AFFECT001 advisory. It exists because docs rot
silently, and this repo has measured that cost. The goal is to fire on real
drift, not to fire less.

ADDITIONAL FIXTURE: a change with no signature and no behaviour delta (a literal
value edit inside one attribute) produces NO AFFECT001 finding and requires no
waiver in source.

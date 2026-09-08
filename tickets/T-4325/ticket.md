---
id: T-4325
title: Citation scan still deadlocks on a changelog entry that quotes a whole directive
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_live_tracker.py
- docs/modules/tickets-landing.md
- tests/test_tickets_live_tracker.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'SCOPE002 closure: existing frob:doc/frob:tests directives on live_tracker_citations
    point at these files'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_tickets_live_tracker.py
  reason: 'SCOPE002 closure: existing frob:doc/frob:tests directives on live_tracker_citations
    point at these files'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE FIX FOR THE CITATION DEADLOCK RECREATED THE DEADLOCK ONE LEVEL UP, AND THE
NEW INSTANCE IS THE FIRST FIX'S OWN CHANGELOG ENTRY.

WHAT HAPPENED, IN ORDER. A ticket could not be closed because narrative prose in a
land-owned changelog quoted a waiver attribute verbatim, and the citation scan
matched the text. That was fixed correctly and generally: a match now only counts
when the matched LINE is itself shaped like a real directive, rather than by
excluding the changelog by path. The reasoning for choosing a parse narrowing over
a path exclusion was sound and is worth preserving.

THE NEW INSTANCE DEFEATS THAT NARROWING HONESTLY. The fix's own changelog entry
describes what it did, and to do so it QUOTES A COMPLETE, WELL-FORMED DIRECTIVE --
the exact text its regression test plants. That quoted line genuinely is shaped
like a directive, so the narrowed filter matches it, correctly by its own rule.
Two sites now cite the still-open ticket: the aggregate changelog and the fragment
it was generated from. Both are land-owned, so no worktree can edit either, and
the ticket is deadlocked again.

THIS IS THE COUNTEREXAMPLE TO THE EARLIER DECISION, AND IT SHOULD BE WEIGHED
HONESTLY RATHER THAN TREATED AS A DEFEAT. The earlier answer -- that land-owned
history should not be excluded by path, since nothing makes a genuine directive
impossible there -- is defensible in principle. What the new instance shows is
that this class of file is generated from Done reports, which routinely quote
directives while describing work, and is simultaneously unwritable by any worktree.
A file that can accumulate arbitrary directive-shaped text and can never be
corrected cannot be a safe source of blocking citations. Decide whether that
combination -- generated from prose AND unwritable -- is the real discriminator,
rather than "land-owned" as such.

CONSIDER THE ALTERNATIVES BEFORE PICKING ONE. Excluding generated history from the
citation scan is the obvious candidate. Another is that a citation should only
block when it lives somewhere a worktree could actually re-point it, which states
the real requirement directly instead of naming paths. A third is that the scan
should ignore quoted or fenced text, though that is a losing arms race against
prose. Whatever you choose, the property to preserve is the earlier fix's: a
GENUINE directive anywhere must still block.

DO NOT SOLVE THIS BY EDITING THE CHANGELOG, and do not add an escape hatch that
lets a close ignore citations generally -- the citation rule exists to stop a
ticket closing while something still points at it, and that is worth keeping.

VERIFY BOTH DIRECTIONS AS THE EARLIER FIX DID: the current two changelog sites must
stop blocking, and a real directive in an ordinary source file must still block.
Then confirm the blocked ticket can actually close, since that is the whole point.

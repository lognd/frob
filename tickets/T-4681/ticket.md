---
id: T-4681
title: 'DECISION: SF-21 -- kernel.md says ''six primitives'' while the parser accepts
  139 keywords; which one moves?'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: medium
parent: T-4667
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: '2026-09-19: DECISION ticket -- its deliverable is an owner
  decision recorded in the body, which legitimately changes no files'
body_changes:
- mode: append
  reason: '2026-09-19: owner decision recorded -- kernel.md is the spec, keywords
    are wired into the kernel rather than deleted, and per-keyword-group leaves are
    filed only after the pessimistic keyword audit (scratchpad/STRATA-KEYWORDS.md)
    lands; ticket stays OPEN as the tracking record until then'
  actor: logan
  at: '2026-09-19'
  old_length: 3425
  new_length: 6683
designated_repro_test: null
acceptance:
- text: 'Owner records a decision in the body: which of the three options (headline
    is right and the implementation should be layered to match, headline is wrong
    and the real surface gets documented, or six core primitives plus named extension
    surfaces), and what it changes. Decided together with T-4678 (SF-09), since options
    1 and 3 both need the same keyword-to-surface table, and with T-3822/T-3823, which
    are the same doc-vs-parser class at statement level.'
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
DECISION TICKET. SF-21 (LOW). Child of story D (T-4667) under epic T-4662.
NOT implementation work. Do not build anything until the owner records a
decision in this body.

EVIDENCE TABLE ROW, VERBATIM FROM scratchpad/STRATA-FRICTION.md:
| SF-21 | Kernel doc says "six primitives"; the parser accepts 139 keywords | docs/strata/kernel.md:9-21 vs strata-core/src/parse/*.rs keyword extraction (139) | doc-drift | LOW |

FULL EVIDENCE (SF-21 section, verbatim):
docs/strata/kernel.md:9 "The six primitives" (Node, Flow, Boundary, Bound,
Claim, Scenario) versus 139 keywords in strata-core's parser and 86 modules /
38,333 lines under src/frob/strata. kernel.md's own later sections (age,
capacity, demand, growth-rate, scenario, verdict, assumption ledger, prover
pipeline) run 761 lines, so the "six primitives" framing survives ONLY IN THE
HEADLINE.

WHY THIS IS A DECISION AND NOT A DOC FIX
The gap is not a stale sentence; it is a question about what strata IS. "Six
primitives" is a design claim, and the owner is currently rethinking the grammar
and semantics -- so whether the headline or the implementation is the thing that
should move is exactly the owner's call, and writing either answer down now
would pre-empt it. The same caveat as SF-09 applies: 139 is a LOWER bound
(keyword-literal extraction only), so the true count is not even known.

OPTIONS THE EVIDENCE SUPPORTS

Option 1 -- the headline is right; the implementation drifted.
Treat Node/Flow/Boundary/Bound/Claim/Scenario as the actual kernel and everything
else as sugar, libraries or std packs layered above it. Would have to change:
docs/strata/kernel.md to state the layering explicitly, and probably the parser
or module structure so the six-primitive core is separable in fact and not only
in prose. Strongest option if SF-09's dead-keyword decision retires surfaces.

Option 2 -- the headline is wrong; document the real surface.
Replace "the six primitives" with an accurate description of the 139-keyword
surface, organised by layer. Would have to change: docs/strata/kernel.md and
probably surface.md. Cheapest, and makes the language honestly bigger.

Option 3 -- keep both, explicitly: six CORE primitives plus named extension
surfaces (std.krb, observability, policy, reliability, ...). Would have to
change: docs plus a registry of which surface each keyword belongs to -- which
is also the artifact SF-09's decision needs to retire or exercise a surface,
so the two decisions produce the same table.

AUDIT BOUNDARY the owner should know: docs/strata/*.md is 8,074 lines across 16
files. The auditor read charter.md, kernel.md (headings + primitives),
surface.md (headings), evidence.md:117 and policy.md by reference. A
line-by-line kernel.md-vs-elaborator diff WAS NOT DONE -- SF-21 is a
headline-level finding, not an exhaustive drift report. If the decision is
option 2 or 3, that exhaustive diff becomes a precondition and should be filed
as its own leaf.

RELATED, already ticketed and attached to story D rather than duplicated:
SF-22 -- T-3822 (docs/strata/surface.md + threat.md show an `attr IDENT` form
the parser does not accept) and T-3823 (docs/strata secret grammar vs charter
prose, `rotate within`/`revoke`). Both are the same doc-vs-parser class at
statement level; this ticket is the same class at framing level. Decide them
together.

ACCEPTANCE
Owner records a decision in the body: which option, and what it changes.


## DECISION RECORDED -- owner, 2026-09-19 19:50

**Decided: option 1, with the opposite disposal rule from the one the option
implied. docs/strata/kernel.md IS the spec. A keyword that produces facts no
primitive owns is NOT deleted -- it is wired into the kernel deliberately, with
a law-1 record -- UNLESS the pessimistic keyword audit proves it was never a
good idea.**

Governing posture, in the owner's words: **"err on the side of adding
capabilities; we originally had a good idea and then forgot to implement it."**

So the gap SF-21 measured -- kernel.md's "six primitives" versus 139 parser
keywords -- is resolved in the kernel's favour as the SPECIFICATION, and against
the kernel as the current IMPLEMENTATION. The six primitives are what strata
means; the 139 keywords are evidence of intent that was never finished. The
default disposition of an unowned keyword is therefore WIRE IT IN, not delete
it, and the burden of proof falls on deletion rather than on retention.

WHAT THIS REJECTS
- Option 2 (the headline is wrong; document the 139-keyword surface as the real
  language) is rejected: it would ratify the drift instead of closing it.
- Option 3 (six core primitives plus named extension surfaces) is not taken as
  framed, because it also treats the unowned keywords as a settled surface to be
  catalogued rather than as unfinished work.
- SF-09's option 1 on T-4678 ("retire the dead surfaces") is pre-empted for the
  same reason. Note that catalogued is not enforced, and neither is catalogued
  the same as decided -- see memory/catalogued-is-not-enforced.md.

THE ONE ESCAPE HATCH, AND THE GATE ON IT
A keyword may be dropped only where **the pessimistic keyword audit proves it
was never a good idea** -- not merely that it is unused. SF-09's measurement
(56 keywords used nowhere, 19 more only in litmus) establishes DISUSE, and the
audit's own boundary note says 139 is a LOWER bound from keyword-literal
extraction, so "unused" is an upper-bound claim about deadness, never a verdict
about value. `confine` is the standing counter-example: implemented, documented
in docs/strata/policy.md, used nowhere, and a real consumer gerrymandered globs
rather than use it (T-3920 item 1). Disuse there measured a discoverability
failure, not a bad idea.

SEQUENCING -- WHY NO LEAVES ARE FILED YET
The pessimistic keyword audit is being written to **scratchpad/STRATA-KEYWORDS.md**
and has not landed. Implementation leaves are filed AFTER it lands, **one per
non-sugar keyword group** (sugar needs no kernel wiring and no law-1 record).
Filing them now would mean guessing the groups, and per
memory/verify-premise-before-filing.md the premise has to be established before
the ticket. This ticket stays OPEN as the tracking record for that follow-up.

DELIVERABLE OF EACH FUTURE LEAF
For its keyword group: the facts the keywords produce, the primitive that owns
them (existing or new), the **law-1 record** for the wiring, the kernel.md
section that now specifies them, and a litmus case that exercises the group --
or, for a group the audit condemns, the argument that it was never a good idea
and the removal.

NEXT ACTION (not this ticket's): land scratchpad/STRATA-KEYWORDS.md, then file
the per-group leaves against this id.

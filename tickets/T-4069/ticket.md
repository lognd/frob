---
id: T-4069
title: 'Three gates were satisfied today by making the code worse: state and audit
  the ''cheapest clearing action'' principle'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
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
THREE GATES WERE SATISFIED TODAY BY MAKING THE CODE WORSE. Each was reported
separately by the same consumer within hours; together they are one property, and
it is the property that most directly undermines this whole system's premise.

THE THREE, ALL MEASURED:
  1. LARGE001 (F-276). T-0240 pushed SpinningShape.tsx to 804 lines and LARGE001
     blocked. The agent TRIMMED COMMENTS to 799 and proceeded. Their words: "a
     size gate that is satisfied by REMOVING DOCUMENTATION has the wrong
     incentive; splitting the file was the right fix but out of the ticket's
     scope."
  2. AFFECT001 (F-277, and F-267 before it). T-0242 swapped Tailwind classes
     (min-h-11 -> min-h-[44px]) across ten files; AFFECT001 demanded a doc touch
     per symbol and the agent added THIRTEEN `frob:waive AFFECT001` COMMENTS TO
     PRODUCTION SOURCE for a styling-only diff with no signature or behaviour
     change.
  3. PARSE002 (F-275). Agents insert an `as` cast purely so the TS walker can
     parse `typeof import()` inside a generic type argument. Their words: "the
     gate is shaping test code."

THE COMMON PROPERTY: IN EACH CASE THE CHEAPEST WAY TO SATISFY THE GATE MAKES THE
CODEBASE WORSE, and the expensive way (split the file, update or correctly scope
the doc, fix the walker) is either out of the ticket's scope or not the author's
to do. So the gate does not merely fail to help -- it actively selects for
deletion of comments, accumulation of waivers, and type-casts written for a
parser rather than for a reader.

WHY THIS DESERVES ITS OWN TICKET RATHER THAN THREE FIXES. Each of the three has
its own ticket already (LARGE001 has none yet, AFFECT001 is T-4054, PARSE002 is
T-4067) and each will be fixed on its own terms. What none of them will produce
is the RULE. A gate that can be satisfied by making the code worse has the wrong
predicate, and that is a property we can state, test for, and apply to gates not
yet written. Without it, the next size/drift/parse rule will be designed the same
way.

WHAT TO PRODUCE:
1. STATE THE PRINCIPLE in the gate-authoring documentation: for every gate, name
   the cheapest action that clears it, and confirm that action improves (or at
   minimum does not degrade) the codebase. If the cheapest clearing action is
   deletion, suppression, or a no-op cast, the predicate is wrong.
2. AUDIT THE EXISTING GATE CATALOGUE against it. This need not be exhaustive to
   be useful -- the size, drift and parse families are the obvious starting set,
   and three measured instances in one day suggests there are more.
3. FOR EACH OFFENDER, prefer changing the PREDICATE over changing the severity.
   LARGE001 counting non-comment lines is a predicate fix; making it a warning is
   not. The consumer's own suggestion for LARGE001 -- count non-comment lines, or
   FILE A SPLIT FOLLOW-UP INSTEAD OF BLOCKING -- is the right shape, and the
   follow-up variant generalises: a gate that detects work the current ticket
   cannot legitimately do should CREATE THE OBLIGATION, not block the ticket.

NOTE THE CONNECTION TO T-4054, which is the same insight from the other side:
there, a ticket could not discharge a doc obligation because the file belonged to
another ticket, and the only reachable mechanism recorded something false. Here
the mechanisms are reachable but degrading. Both are cases where the ESCAPE
AVAILABLE TO THE AUTHOR is worse than the problem being enforced.

DO NOT resolve this by relaxing gates generally. Every one of the three exists
for a real reason -- files do grow unmanageable, docs do rot, unparsed files do
hide defects. The ask is that satisfying them should not require damage.

MUST-FIRE FIXTURE: a gate whose cheapest clearing action is deletion or
suppression is identified by the audit method, on a known example.
MUST-STAY-QUIET: a gate whose cheapest clearing action is a genuine improvement
is not flagged.

ACCEPTANCE
- The principle stated in gate-authoring guidance, in checkable terms.
- The size/drift/parse gate families audited against it, with results per gate.
- Predicate fixes preferred over severity changes, with each choice justified.
- LARGE001 specifically addressed, since it has no ticket of its own.
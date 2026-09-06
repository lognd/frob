---
id: T-4059
title: 'F-261: a wrong-direction frob:tests directive parses silently and only surfaces
  later as a coverage finding'
state: queued
kind: ux
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
- src/frob/graph/dsl.py
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
Consumer logand.app-v2 F-261 (T-0092 agent friction), 2026-09-06:

  "The WRONG-DIRECTION `frob:tests` directive (a PRODUCTION file pointing at a
   test) is ACCEPTED SILENTLY BY THE PARSER and only surfaces as a COV finding
   later; a DSL001-style 'directive points the wrong way' check AT PARSE TIME
   would save a round trip."

THE DIRECTIVE IS ACCEPTED, STORED, AND ONLY CONTRADICTED MUCH LATER. The author
writes something the parser is happy with, work proceeds, and the mistake
resurfaces as a coverage finding whose message is about coverage rather than
about the directive being backwards. So the diagnosis the user needs ("you wrote
this the wrong way round") has to be reconstructed from a symptom that does not
mention it.

WHY A PARSE-TIME CHECK IS THE RIGHT PLACE, and this is more than convenience:
the wrong-direction case is DECIDABLE AT PARSE TIME with information already in
hand -- the directive names a target, and whether the file it sits in is a test
file and whether the target is a test file are both known immediately. Nothing
about detecting it requires the graph, the collectors, or a run. Deferring a
decidable syntactic error to a semantic gate is the same "arrives at the moment
of finishing rather than the moment of writing" class already recorded on T-3939,
T-3950, T-3951 and T-4005 -- this is its fifth instance and the cheapest to fix,
because the check needs no new information.

ONE COMPLICATION THAT MUST BE HANDLED, NOT ASSUMED AWAY: this repo documents that
TWO frob:tests CONVENTIONS COEXIST. From src/frob/gates/__init__.py: "`src` is
the test and `target` is the tested symbol, OR `src` is the tested symbol and
`target` is the test", with `e.src` checked first and `e.target` as a fallback.
So "wrong direction" is not simply "production points at test" -- one of the two
sanctioned conventions IS a production file naming its test. A naive check would
reject correct code.

THAT AMBIGUITY IS PROBABLY THE REAL FINDING. Determine first whether both
conventions are genuinely intended or whether one is a historical accident that
the fallback quietly tolerates. If both are intended, a parse-time check must
accept both and can only flag shapes that fit NEITHER. If only one is intended,
the deliverable is to say so and deprecate the other -- and note T-4014 (TDD001
naming the wrong side as "its verifying test") is very likely the SAME ambiguity
producing a different symptom. Read T-4014 before designing; a single answer
about directive direction would resolve both.

DO NOT ship a check that assumes one convention without settling that question --
it would convert a silent acceptance into a false rejection, which is worse.

ALSO IN THEIR REPORT, recorded but not the subject of this ticket:
  - gate:AFFECT demanded two new exports be named explicitly in an L5 row plus
    `frob ack` on both symbols even though the row already described the
    behaviour -- an agent spent a gate cycle discovering that combination.
  - Three full gates-fast runs were needed to converge on a ONE-FILE change.
Both are cycle-cost complaints consistent with the "gate arrives too late"
cluster above; no separate ticket, but they are evidence for its priority.

MUST-FIRE FIXTURE: a frob:tests directive matching NEITHER sanctioned convention
is reported at parse time, naming the directive and why.
MUST-STAY-QUIET: both sanctioned conventions parse without complaint.
THIRD FIXTURE: the later COV finding for a genuinely wrong directive still fires
-- the parse-time check is an earlier signal, not a replacement.

ACCEPTANCE
- Whether both frob:tests conventions are intended, answered explicitly.
- A parse-time check consistent with that answer, cross-checked against T-4014.
- All three fixtures committed.
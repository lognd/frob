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
body_changes:
- mode: set
  reason: 'apollo reports a second late-detected directive rule: COV002 requires the
    frob:ticket edge to be directly above its symbol, with other frob: directives
    permitted between but an ordinary prose comment breaking the binding -- learned
    only via pre-land sweep refusals. Same shape as the wrong-direction case this
    ticket covers'
  actor: logan
  at: '2026-09-06'
  old_length: 3752
  new_length: 6467
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
## A SECOND LATE-DETECTED DIRECTIVE RULE: COV002 ADJACENCY (apollo, 2026-09-06)

  "COV002 adjacency: a frob:ticket edge SEPARATED FROM ITS SYMBOL BY AN ORDINARY
   PROSE COMMENT LINE does NOT count (the edge must be the line DIRECTLY ABOVE the
   def/assignment, other frob: directives permitted between). Changed TEST
   functions need edges too. BOTH LEARNED VIA T-0136 PRE-LAND SWEEP REFUSALS."

SAME SHAPE AS THIS TICKET'S SUBJECT, DIFFERENT RULE. The wrong-DIRECTION case
above parses silently and surfaces later as a coverage finding. This is the
wrong-POSITION case: a directive that is present, correct, and attached to the
right symbol in every sense a reader would recognise, silently does not count
because one prose comment sits between it and the def. Both are directive
problems that the parser could detect and instead surface at land time.

"BOTH LEARNED VIA PRE-LAND SWEEP REFUSALS" IS THE COST. The adjacency rule is not
discoverable except by violating it, at the most expensive moment -- a pre-land
sweep refusal, after the work is done and staged. An author who writes

    # frob:ticket T-1234
    # this constant is the wire format the collector expects
    KIND = "artifact"

has done something entirely reasonable and gets no signal until land.

THE RULE ITSELF MAY ALSO BE WRONG, and that question should be settled before the
detection is moved earlier. Permitting other frob: directives between the edge and
the symbol but NOT a prose comment is a surprising asymmetry: both are comment
lines, and a prose line explaining WHY a ticket owns a symbol is exactly the kind
of comment this codebase encourages elsewhere. DETERMINE whether the strictness is
load-bearing (is there a real ambiguity a prose line introduces?) or incidental to
how the scan walks upward. If incidental, allow contiguous comment lines of any
kind; if load-bearing, say so in the message.

THE SECOND HALF -- "changed TEST functions need edges too" -- is a separate
surprise worth its own line in whatever documents this: authors reasonably assume
provenance edges are for production symbols.

CROSS-REFERENCE T-4061, which collects the done-report path's undocumented
micro-grammars. This is the same disease in the directive system: rules that are
real, enforced, and stated nowhere the author will look before violating them.
Whoever fixes either should ask whether frob has ANY enumeration of its directive
placement rules, or whether each is embedded in the scanner that enforces it.

ADDITIONAL FIXTURE: a frob:ticket edge separated from its symbol by a prose
comment is either accepted, or reported AT PARSE TIME with a message naming the
adjacency rule -- never silently uncounted until a pre-land sweep.

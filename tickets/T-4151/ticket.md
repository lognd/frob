---
id: T-4151
title: 'WIRE001 answers a call-reachability question with a text scan and reports
  real callers as absent: three consumer false positives in one repo'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'a fourth report refutes the call-shape diagnosis this ticket was filed
    on: the consumer restructured a module-scope call into an ordinary function-body
    call and WIRE001 still flagged it, plus a conventional _build_arg_parser/main
    pair. The real mechanism is that a new caller of a new callee in the SAME DIFF
    is not seen at all, regardless of shape, and frob explore xref resolves the very
    edge the wiring gate misses -- an internal contradiction that should be reproduced
    before any design'
  actor: logan
  at: '2026-09-07'
  old_length: 4440
  new_length: 7620
- mode: append
  reason: record fixture-vs-production scoping observation per T-4191 acceptance
  actor: logan
  at: '2026-09-07'
  old_length: 7620
  new_length: 8297
designated_repro_test: null
acceptance:
- text: given a genuinely uncalled new symbol, when the wiring gate runs, then WIRE001
    still fires
  evidence: []
- text: given a new symbol reached through a collection of callables, by a direct
    call, or by a module-scope call, when the wiring gate runs, then none of the three
    reports WIRE001
  evidence: []
- text: given a new rule id absent from the known-rules set and a new flag destination
    absent from the config copy lists, when the wiring gate runs, then both still
    fire
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
WIRE001 REPORTS REAL CALLERS AS ABSENT, THREE TIMES FROM ONE CONSUMER, all in the
"new symbol has no caller" shape:

  F-330  a caller reached through a tuple-of-callables dispatch table is not
         seen. Worse: the resolver written to work around the blindness then
         tripped a SIZE rule, so the gate's gap manufactured a second finding.
  F-335  a DIRECT call from one function to a new helper records no caller edge.
  F-352  a helper called once at MODULE SCOPE is reported uncalled.

The consumer waived one and filed follow-ups for the others. Three false
positives in one repository, all in the same shape.

THE CAUSE IS DOCUMENTED IN OUR OWN MODULE AND IS NOT A MISTAKE -- WHICH IS WHY
THE FIX IS NOT "USE THE CALL GRAPH". src/frob/gates/_wire.py states plainly that
WIRE001 is deliberately a text scan rather than the reference/call graph, and
gives a sound reason: it must also catch wiring shapes that NEVER APPEAR AS A
CALL TOKEN AT ALL -- a new gate rule id that must appear in a known-rules set, a
new CLI flag whose argparse destination must appear in a config copy list. Those
are strings in lists. No call-graph analysis of any kind can see them. Ripping
out the text scan would silently delete two of the four shapes this gate exists
to catch.

SO THE DEFECT IS NOT THE TEXT SCAN. IT IS USING ONE MECHANISM FOR FOUR QUESTIONS.
The module's own docstring enumerates the four shapes:

    1. a new function/method/class with no non-test caller
    2. a new gate rule id absent from the known-rules set
    3. a new CLI flag destination absent from the config copy lists
    4. a new keyword-only parameter no call site passes

Shapes 2 and 3 are string-in-a-list and a text scan is the ONLY thing that can
answer them. Shape 4 already uses a real parse -- the module says so, diffing the
keyword-only parameter set with the standard library's own parser, and calls that
approach "exact here". Shape 1 is a CALL-REACHABILITY question, the one shape
where a text scan is a proxy for the real answer, and all three consumer reports
are shape 1.

THE PRECEDENT FOR THE FIX IS ALREADY IN THE FILE. Shape 4 was moved to a real
parse and the module documents why that is exact. Do the same for shape 1: answer
it with the call/reference graph, keep the text scan for shapes 2 and 3 where
nothing else works. That also satisfies this project's standing directive that
checks must compare parsed symbols rather than substrings -- applied per question
rather than per gate.

ONE THING TO VERIFY BEFORE BUILDING, because a planner already refuted a related
claim on a sibling ticket: the reference/call graph in this repo resolves edges
to PRIVATE symbols, and WIRE001 deliberately covers PUBLIC additions too, which
the dead-code gate exempts by design. So the graph may not answer shape 1 for
public symbols as it stands. Measure that FIRST. If it does not, the honest
options are to extend the graph's public-symbol resolution or to build a targeted
call-reachability check for this shape -- decide deliberately and record which,
rather than assuming the existing substrate covers it.

ALSO NOTE THE COST SHAPE F-330 EXPOSES, because it raises priority: the gate's
blind spot did not merely produce a false finding, it CAUSED CODE TO BE WRITTEN.
An author added a resolver to make the caller visible, and a second gate then
fired on that resolver's size. A false positive that induces a workaround which
trips another rule is the wrong-incentive class compounding itself.

MUST-FIRE FIXTURE:   a genuinely uncalled new symbol still reports WIRE001.
MUST-STAY-QUIET:     each of the three reported shapes -- reached through a
                     collection of callables, called directly by one function,
                     and called at module scope -- reports nothing.
THIRD FIXTURE:       the string-in-a-list shapes (a new rule id absent from the
                     known-rules set, a new flag destination absent from the
                     config copy lists) still fire, proving the text scan was not
                     removed along with the false positives.

ACCEPTANCE
- Shape 1 answered by parsed call reachability; shapes 2 and 3 still by text scan.
- Whether the existing graph resolves public symbols measured and recorded before
  any design is chosen.
- All three consumer shapes verified quiet, with a fixture each.
- The string-in-a-list shapes proven still caught.
- All three fixtures committed.

A FOURTH REPORT ARRIVED AND IT CORRECTS THE MECHANISM I WROTE ABOVE. F-354 is the
result of the consumer ACTING on F-352's theory, and the experiment came back
negative in a way that is more useful than a confirmation.

They restructured the module-scope call into an ordinary call from inside a
function body -- the exact shape F-352 implied would be traced. WIRE001 STILL
FLAGGED IT. It also flagged a second, entirely conventional pair in the same run:
a `_build_arg_parser` called from `main` in the plainest possible way.

SO "MODULE-SCOPE STATEMENTS ARE NOT TRACED" IS THE WRONG DIAGNOSIS, and my
grouping of F-330/F-335/F-352 above as three variations of call-shape blindness
is too generous to the gate. The actual gap they identified:

    WIRE001 CANNOT SEE A CALL FROM A NEW CALLER TO A NEW CALLEE
    ADDED IN THE SAME DIFF -- regardless of call shape.

F-335 fits this exactly and I had filed it under call shape: its
`resolve_cmd_entry -> _tokenize_cmd` pair was also both-new-in-one-diff. So at
least three of the four reports are one mechanism, and it is not about syntax.

THE DECISIVE EVIDENCE IS AN INTERNAL CONTRADICTION IN OUR OWN TOOLING, and it
should be the first thing reproduced: `frob explore xref` FINDS the call site
correctly, while `frob check --only wire` reports the symbol unwired, on the same
tree in the same state. Two frob commands disagree about whether a call exists.
The one that is right is the one WIRE001 does not consult. That is the clearest
possible demonstration that the substrate to answer shape 1 already exists and
this gate is not using it -- stronger than anything I argued above from the
module docstring.

WHAT THIS CHANGES ABOUT THE FIX
  - The must-stay-quiet fixtures above are necessary but NOT sufficient. Add the
    real one: a diff that adds BOTH a new helper and a new caller of it, in
    non-test files, reports nothing. Prove it for a function-body call AND a
    module-scope call, so a fix for one shape cannot be mistaken for a fix for
    the mechanism.
  - Before designing anything, run the contradiction: take one of their pairs (or
    plant an equivalent), confirm that xref resolves the edge and the wiring gate
    does not, and record both outputs on this ticket. That measurement decides
    whether the fix is "consult the existing graph" or something larger.
  - CHECK WHETHER THE SAME-DIFF EXCLUSION IS DELIBERATE. The gate's stated
    question is whether the new symbol has a caller outside the diff's own TEST
    files -- which reads as excluding tests, not as excluding the diff's own
    non-test code. If some code path is excluding all same-diff callers, find out
    whether that was intended and say so. If it WAS intended, then the rule as
    designed fires on every genuinely new subsystem, which is a design defect
    rather than an implementation one and needs to be argued, not patched.

THE CONSUMER PAID FOR THIS FINDING TWICE, which is worth noting for priority:
they restructured working code on a theory the gate's behaviour implied, and the
restructure bought nothing. A false positive that is also MISLEADING about its
own cause costs more than one that is merely wrong.


OBSERVATION (from T-4191): WIRE001's follow-up requirement (WIRE002) is correct for a production symbol awaiting wiring but wrong for a private per-file test fixture helper -- a fixture will never be wired to production code, so requiring a follow-up ticket for it forces manufacturing a queue entry nobody will ever work. T-4191 pointed such a waiver's follow-up at this ticket instead of inventing one, since this ticket already owns reconsidering WIRE001's subject. This is a scoping question for WIRE002 (or its interaction with WIRE001) worth resolving when this ticket is worked: can the gate distinguish a private test fixture from a production symbol awaiting wiring.
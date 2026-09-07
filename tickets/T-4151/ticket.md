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

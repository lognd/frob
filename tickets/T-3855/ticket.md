---
id: T-3855
title: WIRE001 has no typing.Protocol awareness, so a Protocol member needs a waiver
  whose follow_up can never discharge (apollo T-0024)
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: de-backtick citations that cannot resolve in this repo (proposed artifacts,
    a proposed verb, sibling-repo paths); they are prose, not pointers, and were blocking
    every land touching the docptr gate
  actor: logan
  at: '2026-09-05'
  old_length: 4180
  new_length: 4180
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Parked in a consumer repo: ../apollo T-0024 (queued). It exists ONLY to hold a
follow_up pointer that can never resolve, which is the defect.

APOLLO'S SITUATION, in their words: "src/apollo/report/terminal.py::_IsattyStream"
(a structural `typing.Protocol`) and its `isatty` method, plus the mirroring
test double "tests/unit/test_report.py::_FakeStream.isatty", carry
`frob:waive WIRE001` markers. gate:WIRE requires every WIRE001 waiver to bind a
`follow_up=T-####`. But -- their words -- "a Protocol method body is literally
'...' and is never called through the call graph gate:WIRE inspects, so there is
no future landing that resolves them the way other WIRE001 waivers resolve (a
caller wiring the symbol in)."

So they filed a ticket whose stated purpose is to hold a pointer, and whose own
acceptance is "confirm there is nothing to wire and either teach gate:WIRE to
recognize typing.Protocol members as exempt, or close this as a permanent
no-op waiver."

VERIFIED IN FROB, 2026-09-05: `git grep -in protocol -- src/frob/gates/_wire.py`
returns NOTHING. WIRE001 has no `typing.Protocol` awareness whatsoever.

WHY THIS IS A REAL DEFECT AND NOT PEDANTRY. `follow_up=T-####` exists so a
waiver is temporary: it names the work that will make the waiver unnecessary.
For a Protocol member there IS no such work -- the symbol is uncallable BY
CONSTRUCTION, since a Protocol body is `...` and conformance is structural, not
by call. Requiring a follow-up here forces a permanent ticket that can never be
closed honestly, which is the third instance of this exact shape found today:

  - T-3843: a DOC006 finding in YAML frontmatter, unwaivable because the waive
    form is an inline HTML comment that cannot exist in a YAML scalar.
  - T-3852: a container ticket unclosable because MissingEvidence and
    EvidenceScopeUnbound compose into a state with no exit.
  - this one: a WIRE001 waiver that cannot ever discharge its follow_up.

The pattern is a rule demanding something the subject STRUCTURALLY cannot
provide, with no exit. Worth naming as a class in the done report.

THE CHOICE, AND APOLLO ALREADY FRAMED IT CORRECTLY:
  (a) Teach WIRE001 to recognize `typing.Protocol` members as exempt -- no
      waiver needed at all, so no follow_up question arises. This is the real
      fix: an uncallable-by-construction symbol is not an unwired symbol.
  (b) Allow a permanent no-op waiver form (a waiver that declares itself
      terminal instead of naming a follow-up).
(a) is almost certainly right, and it generalizes: the same argument applies to
`abstractmethod` bodies, `@overload` stubs, and `if TYPE_CHECKING:` symbols --
all uncallable through the call graph for the same structural reason. ENUMERATE
those and say which are in scope; fixing only Protocol leaves the next one to be
discovered the same way, by a consumer repo filing a ticket it cannot action.

(b) may still be worth having independently -- there are permanent waivers that
are not about uncallable symbols -- but do not use it as the answer HERE, and if
you build it, do not let it become the easy escape that stops (a) from
happening.

CHECK THE TEST-DOUBLE CASE TOO. Apollo names `_FakeStream.isatty`, a test double
mirroring the Protocol. That is NOT a Protocol member -- it is a real method with
a real body that is genuinely never called directly (the code under test calls
it through the Protocol). Decide whether it is covered by (a) or needs its own
answer; do not assume the two cases are the same just because they appear in one
ticket.

MUST-FIRE FIXTURE:   a genuinely unwired ordinary symbol still raises WIRE001.
MUST-STAY-QUIET:     a typing.Protocol member raises nothing and needs no waiver.
THIRD FIXTURE:       whichever of abstractmethod/overload/TYPE_CHECKING is
                     brought into scope, proven exempt.

ACCEPTANCE
- (a) implemented, or a reasoned argument for (b) instead.
- The uncallable-by-construction family enumerated, with each member marked in
  or out of scope and why.
- The test-double case decided explicitly.
- All fixtures committed.
- ../apollo is READ-ONLY. Their T-0024 closes on their side once this lands;
  do not touch their tree.

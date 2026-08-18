---
id: T-2523
title: wire check_ambient_capability_reasons into a gate and backfill the 27 reasonless
  ambient grants
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: T-2501
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
- design/frob.strata
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
T-2503 (landed a1c49a2a5) implemented and tested
`frob.strata._effects.check_ambient_capability_reasons()` +
`AmbientCapabilityReasonViolation`, enforcing the rule that an AMBIENT
(via-less, whole-node) capability grant must carry a written reason.

It is NOT WIRED INTO ANY GATE. That was a deliberate, disclosed cut, not
an oversight: wiring it immediately surfaces 27 pre-existing ambient `may`
declarations elsewhere in `design/frob.strata` that have no reason
comment, which is backfill work outside T-2503's declared scope.

This ticket is that wiring plus the backfill.

WHY IT MATTERS THAT THIS DOES NOT SIT UNWIRED: an implemented,
tested, unreferenced check is indistinguishable from no check at all
from the operator's side, and this repo has a documented history of
registry/detector work that shipped catalogued-but-not-enforced and
read as done. T-2503's whole security argument rests on GUARD 1 -- an
ambient grant WITHOUT a justification is exactly the
exemption-that-matches-the-normal-case failure, and the reason text is
the only thing making an ambient grant auditable. Unwired, that guard
does not exist; the 3 ambient grants T-2503 introduced happen to carry
reasons because its author wrote them, and nothing stops the 4th from
omitting one.

DELIVERABLE:
1. Wire `check_ambient_capability_reasons` into the gate that already
   evaluates the strata self-audit family, at the same severity as its
   siblings.
2. Backfill reason comments on the 27 pre-existing ambient declarations.
   A reason must state WHY the capability is expected of every file in
   the node's code glob -- not restate what the grant does. "the suite's
   purpose is executing frob under test" is a reason; "tests exec" is
   not. If a declaration turns out NOT to deserve ambient status, convert
   it to an enumerated `via` list instead of inventing a justification --
   report any you convert.

POSITIVE CONTROLS, BOTH DIRECTIONS:
- an ambient grant with no reason comment must FIRE once wired;
- every one of the 27 after backfill, plus T-2503's own 3, must NOT fire;
- an ENUMERATED (`via`-populated) grant must never require a reason --
  the enumeration is its own justification, and firing on those would
  make the check unusable.

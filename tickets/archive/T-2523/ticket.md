---
id: T-2523
title: wire check_ambient_capability_reasons into a gate and backfill the 27 reasonless
  ambient grants
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: T-2501
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- design/frob.strata
- src/frob/gates/_sys_selfaudit.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/unit/strata/test_effects.py
- src/frob/strata/_effects.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_sys_selfaudit.py
  reason: the SYS111 precedent this ticket must mirror (wire check_ambient_capability_reasons
    at the same severity as its siblings) lives entirely in _selfaudit_violations,
    this file's own function -- the wiring cannot happen anywhere else
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: SYS112 (the new sub-rule this ticket wires) must be added to _KNOWN_GATE_RULES,
    mirroring SYS111's own registry entry, or GATERULE001 flags it as an unregistered
    gate rule id
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/gates.md
  reason: SYS112 must be added to the frob:enumerates rule-id list (mirrors every
    other SYS1xx rule) plus a doc section for the new sub-check, matching SYS111's
    own docs/modules/gates.md section
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/strata/test_effects.py
  reason: node-label coverage for check_ambient_capability_reasons's new node field,
    required by SCOPE002 since the wiring in _sys_selfaudit.py cites it
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/strata/_effects.py
  reason: 'SCOPE001: the ticket''s own new tests import check_ambient_capability_reasons/AmbientCapabilityReasonViolation
    directly from _effects.py -- the file this whole ticket wires and backfills, needs
    to be in scope'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_gates.py
  reason: BUG002 needs a real repro test for the SYS112 wiring itself (parent=unwired,
    fix=wired) -- the existing tests/unit/strata/test_effects.py coverage only tests
    check_ambient_capability_reasons in isolation, which existed unchanged since T-2503
    and cannot distinguish parent from fix
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_missing_reason_is_flagged
- tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_node_label_resolves_the_nearest_preceding_header
- tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_reason_present_is_silent
- tests/unit/strata/test_effects.py::TestAmbientCapabilityReason::test_enumerated_grant_needs_no_reason
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_sys112_ambient_reason_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_sys112_silent_with_a_because_reason
designated_repro_test: tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_sys112_ambient_reason_violation
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: c44342c5cb0edcf99b06ca9c3935f8fecb981086
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
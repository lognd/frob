---
id: T-2530
title: 'strata fragment merge is extend-only by implementation, not by type: seal
  the grant mapping'
state: done
kind: security
origin: human
created: '2026-08-18'
priority: high
parent: T-2501
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_multifile.py
- tests/unit/strata/test_fragments.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_fragments.py
  reason: T-2530's positive controls live in the same test file T-2502 created for
    the fragment mechanism -- adding a TestSealedGrantSet class there, not a new file
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/strata/surface.md
  reason: SealedGrantSet's frob:doc anchor already points here (#fragments-t-2502);
    documenting the sealed-type change belongs in the same section
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_declared_atom_still_works
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_widen_on_undeclared_atom_refuses_closed
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_fresh_insert_raises_at_runtime
- tests/unit/strata/test_fragments.py::TestSealedGrantSet::test_fresh_insert_fails_static_type_check
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2502 (landed d520179c0) shipped the strata fragment mechanism with
extend-only enforcement in two layers, and its author drew a distinction
worth acting on rather than filing away:

LAYER 1 -- Rust grammar -- is structural in the STRONG sense.
`Parser::parse_extend_node` recognizes exactly one clause shape
(`may "ATOM" via GLOB[, GLOB...]`) and has no production for `clearance`,
`capacity`, or any other NodeDecl field inside an `extend` block. A
fragment attempting to weaken a root cannot be SPELLED. That is not a
check that can be forgotten or bypassed; it is an absent grammar rule.

LAYER 2 -- the Python merge (`_multifile.resolve_fragments` /
`_widen_node_grants`) -- is NOT. It is correct-by-current-implementation.
The function today only ever takes the elementwise union of `via` tuples
onto an ALREADY-PRESENT atom, and refuses the whole load closed on an
unknown atom ("a fragment cannot grant a capability the root refused").
But nothing at the type level enforces that this is the only operation it
can perform. A future edit adding `else: node_grants[atom] = grant` for
the unknown-atom case would silently convert fragments from
extend-only into a place to grant capabilities the root refused, and
neither the grammar nor the pydantic models would object.

WHY THIS IS WORTH CLOSING RATHER THAN NOTING. The whole security argument
for fragments is that a fragment cannot weaken a root declaration. This
repo has already paid once for an exemption that quietly matched the
normal case (T-1967), and the capability model's value rests entirely on
grants being auditable at the root. A mechanism whose safety property
holds only as long as nobody edits one function the wrong way is exactly
the shape that survives review and then decays.

DELIVERABLE, as the T-2502 author suggested: introduce a sealed grant
type that the merge can only UNION INTO, never CONSTRUCT FRESH -- so
"insert a new atom" is not an expressible operation in the merge path
rather than an unexercised branch. Concretely, the merge should receive
grants in a form whose only public mutator is a union-with-existing, with
construction restricted to the root-parsing path.

Do NOT settle for adding a test that asserts the current behaviour --
T-2502 already has those, and they are what makes this
correct-by-implementation rather than correct-by-type. The point of this
ticket is to move the guarantee from the test suite into the type system.

If it turns out this cannot be expressed cleanly in Python without
significant contortion, that is a legitimate finding: say so, describe
what you tried, and propose the next-best enforcement (e.g. a structural
gate that refuses any assignment into a node's grant mapping outside the
root parser). Do not ship contortion for its own sake.

POSITIVE CONTROLS, BOTH DIRECTIONS:
- a fragment extending an ALREADY-DECLARED atom must still load and take
  effect (the mechanism must keep working);
- a fragment naming an atom the root never granted must still refuse
  closed;
- and the new one this ticket adds: an attempt IN THE MERGE CODE ITSELF
  to introduce a fresh atom must fail to type-check or fail at
  construction, not merely fail a test.

ALSO NOTED by T-2502's author, lower priority, same file:
`resolve_fragments` folds ALL of a fragment's extend statements into
`errors` collectively rather than short-circuiting per node. Behaviour is
correct today and verified; there is no code-level guarantee against a
future refactor loosening that fold. Address it here only if it falls out
naturally.
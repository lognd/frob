---
id: T-1652
title: Fix DEAD001 unset symref + add pydantic-validator/autouse-fixture rescues
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_wire.py
- src/frob/tickets/_models.py
- src/frob/_cli_parsers/_explore.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/security/_redact.py
- src/frob/tickets/_land.py
- src/frob/vet/_capability_core.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestDeadSymbolGate::test_waiver_directly_above_symbol_suppresses_it
- tests/test_gates.py::TestDeadSymbolGate::test_called_private_helper_is_not_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_pydantic_field_validator_is_not_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_autouse_pytest_fixture_is_not_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_dunder_method_is_not_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_test_function_is_not_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_tests_edge_target_is_not_flagged
- tests/test_gates.py::TestDeadSymbolGate::test_unwired_private_function_is_flagged
designated_repro_test: null
threat: null
component: null
---
DEAD001's Violation never populated `symref` (only file/line), so
`_match_waiver`'s symbol-exact matching path (`violation.symref is not
None`) was structurally unreachable for every DEAD001 finding -- every
`frob:waive DEAD001` placed directly above the flagged symbol (the exact
pattern the gate's own message recommends) silently fell through to the
file-scoped fallback instead, which matches ANY DEAD001 finding anywhere
in that same file (`waiver_file == violation.file`), not just the one it
was written for. Confirmed empirically: 44 of 62 raw DEAD001 findings on
this repo's own tree were already "waived" this way before the fix, with
2 of those (TicketSpec._validate_blocked_by_field/_validate_parent_field)
turning out to be OVER-broadly suppressed by an unrelated single-symbol
waiver 373 lines away in the same file.

Fix: `dead_symbol_gate` now sets `symref=symref` on the `Violation` it
builds, so a waiver placed directly above its target symbol binds
precisely via the symbol-exact path, and no longer over-reaches to every
other DEAD001 finding in the same file.

Also lands two rule-level rescues DEAD001 was missing (found while
investigating why real findings remained after the symref fix):
- `_is_pydantic_validator`: an `@field_validator`/`@model_validator`
  decorated method is dispatched by pydantic's own decorator registry,
  never a call token -- 9 of this repo's own findings were exactly this
  shape.
- `_is_autouse_pytest_fixture`: moved from `frob.gates._wire` (WIRE001's
  own T-1510 rescue) into `_dead_symbols.py` and reused by DEAD001 too
  (`_wire.py` now imports it back rather than duplicating) -- 5 of this
  repo's own findings were autouse pytest fixtures DEAD001 had no
  exemption for at all.

Net effect measured on this repo's own tree: DEAD001 warnings 18 -> 0
(unscoped, FROB_NO_GATE_CACHE=1).
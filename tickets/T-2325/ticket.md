---
id: T-2325
title: WIRE001 does not rescue pydantic model_validator, contradicting WAIVE008's
  own assumption
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_wire.py
- src/frob/gates/_waive.py
- tests/unit/test_wire001_pydantic_validator_rescue.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_wire001_pydantic_validator_rescue.py
  reason: must-fail fixture for the WIRE001 pydantic-validator rescue fix
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_fresh_model_validator_is_not_flagged
- tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_fresh_field_validator_is_not_flagged
- tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_ordinary_new_function_still_flagged_positive_control
designated_repro_test: null
acceptance:
- text: given a fresh pydantic model_validator with no explicit outside caller, when
    WIRE001 runs, then it either recognizes the validator as rescued (matching WAIVE008's
    existing assumption) or WAIVE008 is corrected to stop assuming that rescue exists
  evidence:
  - tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_fresh_model_validator_is_not_flagged
  - tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_fresh_field_validator_is_not_flagged
  - tests/unit/test_wire001_pydantic_validator_rescue.py::TestWire001PydanticValidatorRescue::test_ordinary_new_function_still_flagged_positive_control
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2302: WIRE001's own gate logic
(src/frob/gates/_wire.py) rescues an autouse pytest fixture
(`_is_autouse_pytest_fixture`, imported from
`frob.gates._dead_symbols`) but does NOT import or check
`_is_pydantic_validator` -- so a brand-new pydantic `@model_validator`
method with no explicit caller outside its own tests still fires
WIRE001, even though it IS reachable, dynamically, via pydantic's own
validation dispatch.

Meanwhile `frob.gates._waive`'s WAIVE008 check (the "does this
frob:waive WIRE001 waiver ever suppress anything" liveness check) DOES
import and use `_is_pydantic_validator` (alongside
`_is_autouse_pytest_fixture`) to decide whether a WIRE001 waiver on a
given symbol could ever fire -- so WAIVE008 assumes pydantic validators
are ALREADY exempted by WIRE001 itself, when they are not.

Net effect: a genuinely-fresh pydantic `model_validator` gets WIRE001
(real, unwaived error) if left unwaived, and WAIVE008 (real, unwaived
error, "this waiver suppresses nothing, remove it") if a
`frob:waive WIRE001` is added -- there is no clean way to pass both
checks for this shape today. Confirmed directly: T-2302 added
`TicketSpec._validate_scope_breadth_ack` as a `@model_validator
(mode="after")` and reproduced both findings; worked around by moving
the check to a plain function-level guard in
`_validate_new_ticket_spec` instead (see that function's own updated
docstring for the detail), so this ticket does not fix the gate
inconsistency itself, only documents and routes around it.

REQUIRED: either (a) add `_is_pydantic_validator` to WIRE001's own
rescue predicate in src/frob/gates/_wire.py (mirroring the autouse-
fixture rescue), making it consistent with what WAIVE008 already
assumes, or (b) if there is a reason pydantic validators should NOT be
rescued by WIRE001 (e.g. a validator with a genuinely dead/unreachable
body should still be caught), instead correct WAIVE008 to stop assuming
they are exempted. Pick one; the current state has the two checks
actively disagreeing about the same symbol shape.
---
id: T-1510
title: WIRE001 static caller search cannot see autouse pytest fixtures (test_check_ts_runners.py::_npx_available)
state: done
kind: bug
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_check_ts_runners.py
- src/frob/gates/_wire.py
- tests/unit/test_wire_autouse_fixture.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_wire.py
  reason: WIRE001's autouse-fixture fix lives in the gate module; new dedicated unit
    test file for positive/negative coverage since tests/test_gates.py is leased by
    T-1205
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_wire_autouse_fixture.py
  reason: WIRE001's autouse-fixture fix lives in the gate module; new dedicated unit
    test file for positive/negative coverage since tests/test_gates.py is leased by
    T-1205
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_wire_autouse_fixture.py::TestWireGateAutouseFixtureExemption::test_new_autouse_fixture_is_not_flagged
- tests/unit/test_wire_autouse_fixture.py::TestWireGateAutouseFixtureExemption::test_new_plain_test_helper_with_no_caller_is_still_flagged
- tests/unit/test_wire_autouse_fixture.py::TestWireGateAutouseFixtureExemption::test_non_autouse_fixture_with_no_caller_is_still_flagged
- tests/unit/test_check_ts_runners.py::TestRunTscRealPaths::test_success_parses_clean_output
designated_repro_test: null
threat: null
component: null
---
WIRE001 flags _npx_available in tests/unit/test_check_ts_runners.py as unreached
outside its own tests. It is an autouse pytest fixture, wired in by pytest's own
fixture-injection machinery for every test in this file -- not a direct-call
relationship WIRE001's static caller search can see -- the standard pytest fixture
idiom, not dead code. Follow-up: teach WIRE001's static caller search to recognize
an autouse fixture's implicit per-test invocation (pytest.fixture(autouse=True))
as a reached use, so files relying on this idiom stop needing a per-fixture
frob:waive WIRE001 waiver.
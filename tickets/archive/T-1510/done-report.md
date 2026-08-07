## Done report

Taught WIRE001's static caller search to recognize an
@pytest.fixture(autouse=True) (or pytest_asyncio.fixture) decorated
symbol as reached: `_is_autouse_pytest_fixture` (src/frob/gates/_wire.py)
scans the symbol's own span for the decorator (the parser already
includes the decorator line in a record's span, verified directly), and
`_new_callable_records` now excludes any such symbol from candidacy
alongside the existing dunder/test-symbol exemptions -- pytest's own
fixture-injection machinery reaches an autouse fixture implicitly for
every test in scope, never via a direct call token this gate's text scan
can see.

Removed the per-fixture WIRE001 waiver this fix makes unnecessary from
tests/unit/test_check_ts_runners.py::_npx_available (the ticket's own
motivating instance) and confirmed no other file in the tree carries a
follow_up="T-1510" waiver (grep -rl was empty).

Added tests/unit/test_wire_autouse_fixture.py with one positive case
(new autouse fixture: not flagged) and two negative controls (an
ordinary new private test helper with no caller: still flagged; a
non-autouse @pytest.fixture with no caller: still flagged, since that
shape is out of this ticket's scope). Placed in a new file rather than
tests/test_gates.py::TestWireGate (that file's tests/** lease was held
by concurrent in-progress T-1205 at scope-add time).


Waiver deletion in branch history (intentional, sibling T-1511's work on this same branch): tests/unit/test_check_native_cargo_runners.py:WIRE001 -- removed because T-1511 promoted _FakeCompletedProcess to the shared tests/unit/conftest.py, making the fixture-stand-in waiver obsolete. Declared here because that file is in T-1511's scope, not T-1510's, and the history scan attributes the whole branch to the landing ticket (T-1550 tracks the structural fix).

### Changed
```
 src/frob/gates/_wire.py                       |  47 +++++-
 tests/unit/conftest.py                        |  24 +++
 tests/unit/test_check_native_cargo_runners.py |  14 +-
 tests/unit/test_check_ts_runners.py           |  18 +--
 tests/unit/test_wire_autouse_fixture.py       | 129 ++++++++++++++++
 tickets.md                                    | 208 +++++++++++++++++++++++++-
 6 files changed, 400 insertions(+), 40 deletions(-)
```

### Evidence
- `tests/unit/test_wire_autouse_fixture.py::TestWireGateAutouseFixtureExemption::test_new_autouse_fixture_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire_autouse_fixture.py::TestWireGateAutouseFixtureExemption::test_new_plain_test_helper_with_no_caller_is_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire_autouse_fixture.py::TestWireGateAutouseFixtureExemption::test_non_autouse_fixture_with_no_caller_is_still_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_ts_runners.py::TestRunTscRealPaths::test_success_parses_clean_output` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

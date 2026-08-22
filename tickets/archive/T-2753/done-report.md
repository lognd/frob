## Done report

Changed:
src/frob/gates/_wire.py::_is_pytest_fixture
src/frob/gates/_wire.py::_fixture_param_names
src/frob/gates/_wire.py::_is_fixture_consumed_as_parameter
src/frob/gates/_wire.py::_fixture_reach_short_circuit
src/frob/gates/_wire.py::_is_reached_outside_diff_tests

WIRE001's text-scan reach check only rescued an AUTOUSE pytest fixture
outright (_new_callable_records never even asks whether it is reachable
for that case). A non-autouse fixture consumed via pytest's ordinary
dependency-injection shape (declared as a test/fixture function's own
parameter, e.g. def test_x(self, outside_view):) went through the
ordinary call-shaped scan instead, which can never match it -- a
consumed fixture is never followed by a call token. This is the same
class of gap T-2746 closed for @property attribute access, applied to
fixture parameter injection.

Fix: _is_pytest_fixture (any @pytest.fixture/@pytest_asyncio.fixture
decorator, autouse or not -- deliberately WIDER than
_dead_symbols._is_autouse_pytest_fixture, which only matches the
autouse=True case) plus _is_fixture_consumed_as_parameter, which parses
every .py file in the snapshot via ast and asks whether ANY OTHER
function's signature (same file, sibling test file, or a file that
imports the fixture directly) names the fixture as a bare parameter.
_fixture_reach_short_circuit wires this into
_is_reached_outside_diff_tests as the FIRST check for a confirmed
fixture, split into its own function (mirroring the T-1746
_wire_scan_decision precedent) to stay under ARCH001's line threshold.

The real site this closes: tests/unit/test_app_runners_batch6.py::
_real_console_handlers carries `frob:waive WIRE001 follow_up="T-2753"`
(T-2743's SC004 disposition) -- that waiver is intentionally left in
place (waivers are not retroactively removed by a detector fix in this
repo's convention; WIRE002 would fire on a stale unresolved follow_up if
this needed doing, and it does not require doing here).

Evidence:
tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_consumed_by_a_test_in_the_same_file_is_not_flagged
tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_consumed_by_a_test_in_a_different_file_is_not_flagged
tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_consumed_only_by_another_fixture_is_not_flagged
tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_with_no_consumer_anywhere_still_flagged_positive_control
tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_ordinary_new_function_still_flagged_positive_control

Manually confirmed (not asserted in prose): the three negative
(no-longer-flagged) tests FAIL against pre-fix _wire.py (git show
HEAD~1) and PASS after the fix; both positive controls pass at both
revisions -- the fix narrows the false positive, it does not disable
WIRE001. tests/unit/test_wire001_property_attribute_access.py (T-2746,
the analogous property-access fix) and the rest of
tests/test_gates.py -k Wire also re-run clean, aside from one
pre-existing failure (test_new_cli_dest_present_in_config_external_is_not_flagged)
confirmed identical on main before this change -- not a regression.

Filed: none

Gates: frob check --ticket T-2753 clean of new findings -- fixed one
E501 and one ty invalid-return-type introduced by my own first draft
(frozenset(names) return, not set), and split the fixture short-circuit
into its own function to clear an ARCH001 line-count regression on
_is_reached_outside_diff_tests. The 29 errors remaining are pre-existing
baseline noise, none touching the files this ticket changed.

### Changed
```
 tickets/T-2753/ticket.md | 16 +++++++++++++++-
 1 file changed, 15 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_consumed_by_a_test_in_the_same_file_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_consumed_by_a_test_in_a_different_file_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_consumed_only_by_another_fixture_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_fixture_with_no_consumer_anywhere_still_flagged_positive_control` (pytest node id, verified passing when recorded)
- `tests/unit/test_wire001_fixture_parameter_access.py::TestWire001FixtureParameterAccess::test_ordinary_new_function_still_flagged_positive_control` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 18 error(s), 877 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, E501@/home/logan/projects/frob/.claude/worktrees/t2761-series/src/frob/tickets/_new_renumber.py, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md

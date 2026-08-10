## Done report

Implemented the real fix for WIRE001's same-file test-fixture-reuse false
positive (T-1746's option 2): `_wire.py`'s same-file exclusion
(`_wire_test_path_excluded`) is no longer absolute for a test-tree
symbol. `_is_reached_outside_diff_tests` now also scans the symbol's OWN
defining file, but only counts a match as "reached" there when the call
site sits inside a genuine `test_*`-prefixed function/method
(`_enclosing_def_is_test_function`, a lightweight indentation-climbing
text scan -- deliberately not a full AST walk, matching this module's
existing bare-text-scan bias toward recall over precision). A helper
called only from another non-test helper in the same file, never from a
real test, still trips WIRE001 -- the genuinely-unwired case stays
caught.

This let T-1727's `frob:waive WIRE001 ... follow_up="T-1746"` on
`_repo_with_add_change` (tests/test_tickets_mutation_evidence.py) be
removed outright -- the gate itself no longer false-positives on it.

Split `_is_reached_outside_diff_tests`'s per-path scan body into
`_reached_in_file` and the exclusion/require-test-caller decision into
`_wire_scan_decision` to keep the parent function under ARCH001's
60-line threshold.

Updated `tests/test_gates.py::TestWireGate.
test_test_helper_called_only_from_its_own_defining_file_is_still_flagged`
(the test that locked in the OLD, now-superseded behavior) into two
tests: one confirming the new same-file-test-caller allowance, one
confirming the genuinely-unwired same-file case still fires. Fixed the
now-stale evidence citation in the archived T-1558 ticket that named the
old test by its old name.

Changed:
- src/frob/gates/_wire.py: _wire_test_path_excluded (docstring only, no
  behavior change to its own return value), _is_reached_outside_diff_tests
  (now delegates to two new helpers), _wire_scan_decision (new, private),
  _reached_in_file (new, private), _TEST_FUNC_DEF_RE/_ANY_FUNC_DEF_RE (new
  module constants), _enclosing_def_is_test_function (new, private)
- tests/test_gates.py: TestWireGate split test (see above)
- tests/test_tickets_mutation_evidence.py: removed the now-obsolete
  frob:waive WIRE001 on _repo_with_add_change
- tickets/archive/T-1558/ticket.md: fixed stale evidence citation

Evidence:
- tests/test_gates.py::TestWireGate.test_test_helper_called_from_a_real_test_in_the_same_file_is_not_flagged
- tests/test_gates.py::TestWireGate.test_test_helper_called_only_from_a_non_test_helper_is_still_flagged
- 29/29 tests/test_gates.py -k TestWireGate pass
- 18/18 tests/test_tickets_mutation_evidence.py pass

Gates: `uv run frob check --ticket T-1746` (FROB_NO_GATE_CACHE=1, fresh)
exit 0, every gate:* family passes. `uv run frob check --land-parity`
(fresh) reports clean (0 unscoped errors). ruff-check/format failures
present are pre-existing repo-wide debt in files this ticket never
touched, confirmed by re-checking after every edit.

### Changed
```
 design/frob.strata               |  38 ++++-----
 docs/modules/app.md              |  28 +++++++
 src/frob/_cli_parsers/_check.py  |  14 ++++
 src/frob/app/_config_external.py |   2 +
 src/frob/app/check_runner.py     |  77 ++++++++++++++++++
 src/frob/app/config.py           |   6 ++
 src/frob/gates/_waive.py         | 125 ++++++++++++++++++++++++++++
 tests/test_waive_gate.py         | 171 +++++++++++++++++++++++++++++++++++++++
 tickets/T-1746/ticket.md         |  42 +++++++++-
 tickets/T-1764/done-report.md    |  81 +++++++++++++++++++
 tickets/T-1764/ticket.md         |  67 ++++++++++++++-
 11 files changed, 629 insertions(+), 22 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1295 warning(s), 734 waived
- error-findings: none (measured, zero errors)

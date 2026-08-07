## Done report

Taught WIRE001's _is_reached_outside_diff_tests (src/frob/gates/_wire.py) an
ErrorSet-member-access shape: for a CLASS record, a bare `ClassName.Member`
attribute-access token now also counts as "reached" -- a typani ErrorSet
subclass is never referenced call-shaped (ClassName(...)); callers spell it
ClassName.Member, and the class itself otherwise only shows up in a
Result[..., ClassName] annotation, also paren-free. Extracted the pattern-
building into a new _wire_reach_patterns helper (shared by both the T-1502
wrapper-marker shape and this ticket's member-access shape) to keep the
scanning function itself under ARCH001's 60-line threshold.

Removed the frob:waive WIRE001 workaround this exact shape forced onto
src/frob/testing/_coverage_refresh.py::CoverageRefreshError (follow_up="T-1527",
the ticket's own named real-world instance from T-1516); re-ran the scoped
gates and its own tests to confirm the false positive is gone with no waiver
needed. Grepped the repo for any other follow_up="T-1527" citation -- none
found beyond this one.

Added one positive detector test (a new ErrorSet-shaped class referenced only
via bare Member access in a diff-added symbol is no longer flagged) and one
negative test (a class never referenced by call OR member access anywhere
still fires) to TestWireGate in tests/test_gates.py.

### Changed
```
 src/frob/gates/_wire.py   | 19 ++++++++++++--
 src/frob/lang/__init__.py |  9 -------
 tests/test_gates.py       | 65 +++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                | 61 +++++++++++++++++++++++++++++++++++++++++---
 4 files changed, 140 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_new_errorset_class_referenced_by_bare_member_access_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_new_class_never_referenced_by_member_access_is_still_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 232 warning(s), 786 waived
- error-findings: none (measured, zero errors)

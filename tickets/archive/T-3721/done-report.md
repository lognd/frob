## Done report

TEST006's remedy string pointed at 'make coverage', which the scaffold's Makefile intentionally does not ship (its own comment says frob coverage is the interface). Updated the remedy in _test006_missing (src/frob/gates/__init__.py) to say 'frob coverage --full --fail-on-degraded', matching the frob-native coverage path T-3748 shipped. Evidence: tests/gates_suite/test_test_gate.py::TestTestGate::test_test006_remedy_points_at_frob_coverage_not_make (bound). Filed: none. Gates: frob check --ticket T-3721 clean except the pre-existing out-of-scope DEPR006 on frob-deprecated-baseline.lock.json (known, not this ticket's).

### Changed
```
 src/frob/gates/__init__.py          |  7 ++++++-
 tests/gates_suite/test_test_gate.py | 16 ++++++++++++++++
 tickets/T-3721/ticket.md            | 10 +++++++++-
 3 files changed, 31 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/gates_suite/test_test_gate.py::TestTestGate::test_test006_remedy_points_at_frob_coverage_not_make` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4344 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json

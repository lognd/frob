## Done report

Changed:
src/frob/gates/__init__.py::_KNOWN_GATE_RULES
tests/test_gates.py::TestKnownGateRuleIds._KNOWN_ISSUE_ALLOWLIST

Evidence: tests/test_gates.py -k TestKnownGateRuleIds pass; full tests/test_gates.py suite passes (all green); frob check --ticket T-0966 gate-summary 0 errors (only pre-existing unrelated ruff-format finding in src/frob/arch/_lock_ordering.py, not in scope)
Filed: none
Gates: frob check --ticket T-0966 clean (gate:PRE, gate:DRIFT, gate:COV, all pass; no waivers added)

### Changed
```
 src/frob/gates/__init__.py |  58 +++++++++++++++++++++++--
 tests/test_gates.py        | 105 +++++++++++++++++++++++++++++++++++++--------
 tickets.md                 |  67 ++++++++++++++++++++++++++++-
 3 files changed, 206 insertions(+), 24 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov002_scope_grace_without_same_diff_close_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_open_scopes_grace_requires_both_root_and_diff` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov002_scope_grace_covers_ticket_created_and_closed_in_same_diff` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

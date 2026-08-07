## Done report

The REL2xx-REL38x and SYS204 obligation families emitted rule ids built from module-level constants, which T-0901's regex drift-lock never saw (it scans inline rule= string literals only) -- so 30 real, firing rule ids were absent from _KNOWN_GATE_RULES. All 30 registered with citing comments mapping each to its source module; the drift-lock's constant-blindness is a separate follow-up. Verified by direct enumeration of REL_*/SYS_* module constants cross-checked against the registry.

### Changed
```
 src/frob/gates/__init__.py |  63 +++++++++++++++++++++++++++-
 tickets.md                 | 102 ++++++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 163 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

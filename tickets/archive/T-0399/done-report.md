## Done report

Green must claim quality, executed incrementally: measured every WARN family on this repo (PERF 1730, PII 167, SEC110 16, ARCH001 101, WAIVE004 advisory-by-design), promoted the one family that could go blocking without redding main -- dup_gate now fails CLOSED with DUP003 ERROR when [dup].enforce is set but the native is unavailable (before-fails/after-passes proven). A default-on enforce flip was live-tried, measured over the foreground chunk budget (find_clones indexes the full snapshot), reverted, and documented rather than forced. Six burn-down children plus an epic filed with exact counts; the executed plan is recorded in docs/audits/gates-quality.md.

### Changed
```
 docs/audits/gates-quality.md |  56 +++++++
 docs/modules/gates.md        |   6 +-
 frob.toml                    |  18 ++
 src/frob/gates/__init__.py   |  36 +++-
 tests/test_gates.py          |  23 +++
 tickets.md                   | 380 ++++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 513 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

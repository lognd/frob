## Done report

Main sat at 13 gate errors from two lands. The 12 DRIFT002s: T-0715's frob:tests edges used pytest's Class::method separator while the DRIFT resolver matches the obligation graph's dotted Class.method symbol keys (GraphSnapshot.symbols) -- fixed each of the 12 edge targets in place, matching the sibling-edge convention already in the same files. The PARSE002: the intentionally-malformed parser fixture tests/fixtures/lang/broken.py gained an in-file file-scoped frob:waive PARSE002 with a reason, the gate's own endorsed remedy, verified not to perturb the fixture-dependent suites.

### Changed
```
 src/frob/tickets/__init__.py                     | 10 +--
 src/frob/tickets/_models.py                      |  4 +-
 tests/fixtures/lang/broken.py                    |  3 +
 tests/unit/test_app_runners_t0715_sprint_tier.py | 10 +--
 tickets.md                                       | 78 +++++++++++++++++++++++-
 5 files changed, 91 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/test_lang.py::TestErrors::test_syntax_error_yields_partial_symbols` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestParseFailureGate::test_partial_parse_is_an_error_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketNewTierSprint::test_new_carries_tier_and_sprint` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestTierField::test_default_tier_is_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

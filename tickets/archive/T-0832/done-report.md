## Done report

Land claim re-verification now models "could not measure" explicitly:
_check_gates_summary_fn returns None (never -1), DoneReportClaims gate
fields are int|None rendered as an unmeasured marker, and land skips the
gate-state compare with a logged notice when either side is unmeasured --
test-count claims still verified; measurable divergences still refuse.

### Changed
```
 src/frob/app/ticket_runner.py |  31 ++++++++-----
 src/frob/tickets/__init__.py  |  32 ++++++++++++-
 src/frob/tickets/_land.py     |  64 +++++++++++++++++++++++---
 src/frob/tickets/_models.py   |  76 ++++++++++++++++++++++++-------
 tests/test_ticket_land.py     | 102 ++++++++++++++++++++++++++++++++++++++++++
 tickets.md                    |  87 +++++++++++++++++++++++++++++++++--
 6 files changed, 357 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_two_unmeasured_gate_claims_never_vacuously_match` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: -1 error(s), -1 warning(s), -1 waived

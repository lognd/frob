## Done report

Changed:
src/frob/strata/_effects.py::check_stale_via_symbols (WIRE001 waiver removed, now has a real caller)
src/frob/strata/__init__.py (export check_stale_via_symbols, StaleViaSymbolViolation)
src/frob/gates/_sys_selfaudit.py::_selfaudit_violations (folds SYS109 into SELFAUDIT001)
tests/test_gates.py::TestSelfAuditGate.test_selfaudit001_folds_stale_via_symbol_violation
docs/modules/gates.md (SYS109 row, drop GAP note)
docs/strata/surface.md (drop GAP paragraph)

Evidence: tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_stale_via_symbol_violation

Filed: T-1827 (SCOPE001/COV002 implicit-ledger-in-scope rule ignores v2 per-ticket
tickets/<id>/ticket.md; found as an unrelated pre-existing SCOPE001 finding on this ticket's own
tickets/T-1761/ticket.md, not caused by this ticket's edits)

Gates: frob check --ticket T-1761 clean except the pre-existing tickets/T-1761/ticket.md SCOPE001
noise described above (filed as T-1827) and repo-wide pre-existing findings unrelated to
this ticket's touched files (per the gate's own scope-note: only gate:SCOPE/PREWORK and the
diff-driven parts of gate:COV/FMT/AFFECT are ticket-scoped; everything else is repo-wide).

### Changed
```
 tickets/T-1761/ticket.md           | 10 +++++++++-
 tickets/T-1827/ticket.md | 21 +++++++++++++++++++++
 2 files changed, 30 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 4 error(s), 1678 warning(s), 736 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/tickets/_doable.py

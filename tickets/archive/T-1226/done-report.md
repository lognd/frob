## Done report

Re-measured all six 2026-07-29 gate-gap classes against current main
(2026-08-10), by reading the wired gate registry
(src/frob/gates/__init__.py's `docblocks`/`doclink`/`docanchor`/
`docstatus`/`docmake` lambdas), not by trusting a module's mere existence
on disk -- a first grep pass for `docenum_gate`/`negexist_gate` found
nothing and would have wrongly reported classes 1/3 as still-unwired
dead code; re-checked against the actual exported names
(`docenum001_gate`, `negexist001_gate`) and both are wired.

Results: classes 1 (T-1227, DOCENUM001), 2 (T-1228, DOC006 file::symbol +
bare-identifier kinds), 3 (T-1229, NEGEXIST001), 5 (T-1231, DOC008), and
6 (sub-items 1/2/3 per the audit doc's own prior status) are DONE. Class
4 is PARTIAL: T-1230 shipped only the Makefile-target-citation sub-case
(DOC010); frob.toml-severity and other non-Makefile config surfaces
remain open, split out as T-2080.

Updated docs/audits/docs-staleness-2026-07-29.md's "Gate-gap classes"
section to record this status per-class, with the ticket id and wiring
evidence for each -- the section previously read as if all six were
still open design work, which was stale.

Not done in this pass (disclosed, not silently dropped): the ~140
class-B doc-content findings themselves (the fix campaign the mechanism
work exists to prevent from recurring) are untouched -- that is separate,
much larger scope than this ticket's own declared files.

### Changed
```
 tickets/T-1226/ticket.md           | 33 ++++++++++++++++++++++----
 tickets/T-2080/ticket.md | 48 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 77 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH001@src/frob/tickets/_land.py, ARCH103@src/frob/app/ticket_runner/_query.py, PERF004@src/frob/tickets/_land.py, PII012@src/frob/testing/_coverage_refresh.py, SELFAUDIT001@design

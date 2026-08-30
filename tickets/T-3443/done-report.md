## Done report

Ticket's named scope pointed at src/frob/doctor/__init__.py, but doctor is a flat module (src/frob/doctor.py); the actual owning re-export site for scan_external_tools/ToolCategory/ExternalToolStatus is src/frob/__init__.py, added to scope with reason recorded. Added the 3 missing frob.doctor symbols and 3 missing frob.lang._support symbols (PackageAudit, PackageLanguageAxis, unfaceted_packages) to their respective package __init__ import/__all__ lists. Fixed 2 ruff I001 import-sort violations frob fmt introduced. Reproduces locally (pre-existing repo drift, not a CI-only environment issue).

### Changed
```
 src/frob/__init__.py      |  9 +++++++++
 src/frob/lang/__init__.py |  9 +++++++++
 tickets/T-3443/ticket.md  | 13 ++++++++++++-
 3 files changed, 30 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 14 error(s), 4098 warning(s), 856 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@docs/design/windows-portability.md, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3443, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, unresolved-attribute@tests/system/test_coverage_sigterm.py

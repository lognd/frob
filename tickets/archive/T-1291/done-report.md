## Done report

The three flagged 0.0%-branch symbols in src/frob/bind (scan_bindings,
scan_sources, check) already had real behavioral tests: they write real
.cpp/.rs/.h fixture files to tmp_path, run the scanner, and assert on the
actual parsed decls (kinds, signatures) or mismatch output -- not filler.
The 0.0% figure came from a stale/deflated coverage.xml (TEST011: coverage.xml
covers 0% of known modules, predates a tracked source change). No dead code
found; all three are the module's live public API (scan_bindings/scan_sources
are the primitive scanners, check is the cross-reference entry point already
bound to an invariant, INV-007). Re-ran tests: 3 passed. Recorded existing
evidence against the ticket's three acceptance criteria.

### Changed
```
 src/frob/docs/__init__.py         |  21 +++
 src/frob/fleet/__init__.py        |  33 +++++
 tests/unit/fleet/test_manifest.py |  12 ++
 tests/unit/fleet/test_route.py    |  30 ++++
 tests/unit/fleet/test_status.py   | 103 ++++++++++++++
 tests/unit/test_docs_module.py    |  79 +++++++++++
 tickets.md                        | 286 +++++++++++++++++++++++++++++++++++---
 7 files changed, 547 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/unit/test_bind.py::test_scan_bindings_finds_cpp_and_rust` (pytest node id, verified passing when recorded)
- `tests/unit/test_bind.py::test_scan_sources_finds_header_and_rust` (pytest node id, verified passing when recorded)
- `tests/unit/test_bind.py::test_check_reports_mismatch_for_unbound_binding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 3 error(s), 355 warning(s), 675 waived
- error-findings: OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, SELFAUDIT001@design

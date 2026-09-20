## Done report

T-4459's ImportSourceStatus was added to src/frob/doctor.py but never
registered as public API in src/frob/__init__.py, so frob-exports
reported it missing (CI run 34817719845 failure). It is genuine public
API -- part of DoctorReport's contract, same posture as
GlobalBinarySkew and DoctorReport's other status/report sibling
dataclasses -- so it is exported, not demoted to private: imported in
src/frob/__init__.py and added to __all__ alphabetically, matching
DoctorReport's own existing pattern exactly.

Evidence:
tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
-- real repro confirmed via --check-repro (FAILED_AT_PARENT, no BUG002
waiver needed).

### Changed
```
 src/frob/__init__.py     | 2 ++
 tickets/T-4482/ticket.md | 2 ++
 2 files changed, 4 insertions(+)
```

### Evidence
- `tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

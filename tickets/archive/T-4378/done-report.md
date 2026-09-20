## Done report

T-4378: test_current_pin_passes_serve_extra_check asserted the whole smoke scripts returncode, which also depends on check_base_installs frob doctor toolchain (ruff/ty) inventory -- an ambient-PATH fact of the CI runner, not the serve extras own health. Fixed by asserting the serve-extra PASS/FAIL markers directly, test-only; scripts/artifact_smoke.py and src/frob/doctor.py unchanged so the real release-gating smoke check is unaffected.

### Changed
```
 tests/system/test_artifact_smoke.py | 26 +++++++++++++++++++++++---
 tickets/T-4378/ticket.md            | 15 ++++++++++++++-
 2 files changed, 37 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/system/test_artifact_smoke.py::TestArtifactSmokeMustStayQuiet::test_current_pin_passes_serve_extra_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4774 warning(s), 958 waived
- error-findings: none (measured, zero errors)

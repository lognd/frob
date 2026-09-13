## Done report

Fixed the three-layer stale-core-wheel gap (cache key, target/wheels rebuild, version-pin preflight); unit+ci-workflow tests green; CROSSTICKET/SCOPE on docs/guides/release.md remain because T-4464 also owns that file and is still in-progress -- land order or --allow-cross-ticket needed

### Changed
```
 .github/workflows/ci.yml                 |  30 ++++-
 Makefile                                 |  28 +++-
 docs/guides/release.md                   |  24 ++++
 scripts/artifact_smoke.py                | 220 +++++++++++++++++++++++++++++--
 tests/unit/test_artifact_smoke_script.py |  80 +++++++++++
 tickets/T-4465/ticket.md                 |  19 +++
 6 files changed, 386 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_stale_version_wheel_names_versions` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_matching_version_wheel_does_not_raise` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_no_pins_skips_version_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestReadCorePins::test_reads_both_pins_from_metadata` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestReadCorePins::test_unreadable_wheel_returns_empty` (pytest node id, verified passing when recorded)
- `tests/system/test_artifact_smoke.py::TestArtifactSmokeAbsentCores::test_absent_cores_report_named_core_missing` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_both_cores_absent_names_both` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_one_core_absent_names_only_that_one` (pytest node id, verified passing when recorded)
- `tests/unit/test_artifact_smoke_script.py::TestRequireCoreWheels::test_both_cores_present_does_not_raise` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 2 error(s), 4798 warning(s), 962 waived
- error-findings: CROSSTICKET001@docs/guides/release.md, REF002@docs/design/macos-portability.md

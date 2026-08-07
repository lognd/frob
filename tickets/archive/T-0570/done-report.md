## Done report

Scope was empty at dispatch; set to src/frob/doctor.py, docs/guides/install.md,
tests/system/test_cli_doctor.py, tickets.md after checking live leases
(T-0554 holds src/frob/check/, T-0177 holds src/frob/app/**/gates/**/graph/**) --
deliberately kept the entire manifest inside doctor.py itself instead of
touching either leased area.

Added `DERIVED_ARTIFACTS` (a name/path/kind table for `.frob/cache.db`,
`.frob/dup.db`, `.frob/vet.db`, `.frob/coverage-stamp`, `.frob/baseline`,
`frob-coverage.lock.json`), `DerivedArtifactStatus`, `_artifact_status`,
`verify_derived_state`, and folded the result into `DoctorReport` via a new
`derived_state` field. `run_diagnosis(root=None)` now fingerprints (sha256)
every present artifact and validates it (SQLite magic header for the .db
caches, `json.loads` for the JSON stamps), reporting present-but-corrupt
entries with a `detail` string and folding them into the overall
`healthy`/`remediation` verdict alongside the pre-existing native-extension
check -- one clear banner instead of the confusing downstream findings the
T-0517 stale-dup.db and coverage-clobber incidents produced. Absence is
healthy (nothing written yet is not corruption); this only catches
corruption/malformed bytes, not staleness-by-content-drift.

Actually wiring a hard BLOCK into `frob check`/`frob gates` (so corrupt
derived state can't even be consulted, not just flagged) needs
`src/frob/check/**`/`src/frob/gates/**`, both under other agents' live
leases at dispatch time -- filed as a follow-up ticket instead of touching
either.

### Changed
```
 docs/guides/install.md          |  47 ++++++++++
 src/frob/doctor.py              | 198 ++++++++++++++++++++++++++++++++++++++--
 tests/system/test_cli_doctor.py | 110 ++++++++++++++++++++++
 tickets.md                      | 111 +++++++++++++++++++++-
 4 files changed, 452 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_reports_healthy_when_natives_present` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_json_reports_healthy_when_natives_present` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_fails_loud_when_native_missing` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorCli::test_doctor_json_fails_loud_when_native_missing` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_reports_absent_as_healthy` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_corrupt_sqlite_cache` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_flags_malformed_json_stamp` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_verify_derived_state_accepts_valid_json_stamp` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_unhealthy_when_derived_state_corrupt` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state` (pytest node id, verified passing when recorded)

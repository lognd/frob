## Done report

Changed:
.github/workflows/release.yml::jobs.build (macos-x86_64/manylinux-aarch64 matrix entries, cross field, timeout-minutes, import-smoke skip)
.github/workflows/release.yml::jobs.artifact-smoke (macos-x86_64 dropped, timeout-minutes)
tests/unit/test_release_workflow_gate.py::TestCiStatusGate.test_artifact_smoke_covers_every_build_target
tests/unit/test_release_workflow_gate.py::TestNoRetiredRunnerImages
tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke
docs/guides/release.md (cross-build + runner-image-rule + aarch64-addendum notes)

Evidence (frob:tests T-4470):
tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_artifact_smoke_covers_every_build_target
tests/unit/test_release_workflow_gate.py::TestNoRetiredRunnerImages::test_no_matrix_entry_uses_a_retired_image
tests/unit/test_release_workflow_gate.py::TestNoRetiredRunnerImages::test_build_and_artifact_smoke_jobs_have_timeout_minutes
tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_expected_targets_are_marked_cross
tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_native_targets_are_not_marked_cross
tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_import_smoke_step_branches_on_matrix_cross
Full file: pytest tests/unit/test_release_workflow_gate.py -q -p no:randomly -> 37 passed
YAML validated with python yaml.safe_load

Filed: none

Gates: frob check --ticket T-4470 clean against scope (2 pre-existing
out-of-scope findings remain -- DRIFT001 on src/frob/doctor.py and
REF002 on docs/design/macos-portability.md -- neither touched by this
ticket's diff). BUG002 waived via frob ticket body --append-file,
reason: CI-config change with no local fail-before/pass-after repro
path (see ticket body).

Decision recorded: artifact-smoke's macos-x86_64 leg is DROPPED (not
faked with an unverified Rosetta/uv-managed x86_64 interpreter,
PLATFORM001) since that job runs real frob commands, not just an
import; the x86_64 wheel is still built and retained as a CI artifact
via build. manylinux-aarch64 (coordinator addendum, run 34781548188)
is handled the same way as macos-x86_64 for build's import-smoke step
(cross: true field, generic skip) but was NOT dropped from
artifact-smoke -- no evidence it fails there was reported.

### Changed
```
 .github/workflows/release.yml            |  66 +++++++++++++++-
 docs/guides/release.md                   |  52 +++++++++++++
 tests/unit/test_release_workflow_gate.py | 130 ++++++++++++++++++++++++++++++-
 tickets/T-4470/done-report.md            |  25 ++++++
 tickets/T-4470/ticket.md                 |   7 ++
 5 files changed, 274 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_release_workflow_gate.py::TestCiStatusGate::test_artifact_smoke_covers_every_build_target` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestNoRetiredRunnerImages::test_no_matrix_entry_uses_a_retired_image` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestNoRetiredRunnerImages::test_build_and_artifact_smoke_jobs_have_timeout_minutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_expected_targets_are_marked_cross` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_native_targets_are_not_marked_cross` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCrossBuiltTargetsSkipImportSmoke::test_import_smoke_step_branches_on_matrix_cross` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 2 error(s), 4804 warning(s), 967 waived
- error-findings: DRIFT001@src/frob/doctor.py, REF002@docs/design/macos-portability.md

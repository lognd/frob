## Done report

Added Unity toolchain detection to frob doctor (T-4501): reuses T-4515's detect_unity_project(root) (frob.lang._project_detect) to report a Unity project's editor version, gated so a non-Unity root never attempts Unity detection at all (criterion 3). Added _locate_unity_editor (env UNITY_PATH/UNITY_EDITOR -> Unity Hub default install roots per OS -> PATH) as an OPTIONAL tool -- absence reported via UnityEditorStatus(present=False), never a doctor health failure (criteria 1/2). Added dotnet as a plain OPTIONAL _EXTERNAL_TOOLS entry alongside cargo/npm/ctest. New DoctorReport.unity_project/unity_editor fields, both None outside a Unity project, never affecting healthy. Measured: tests/unit/test_doctor.py 17/17 pass (was 13, +4 new test classes covering all 3 acceptance criteria); ruff check/format clean on src/frob/doctor.py and tests/unit/test_doctor.py. Acked src/frob/doctor.py::run_diagnosis (DRIFT001, digest moved after wiring in Unity calls). Fixed gate:SEC (SEC110 x2, inline frob:waive -- PROGRAMFILES/UNITY_PATH/UNITY_EDITOR carry no secret). gate:SELFAUDIT (SELFAUDIT001 x2, env.read observed at doctor.py but not declared in design/frob.strata cli-node via-list) could NOT be fixed in-scope: design/frob.strata is LIVE-leased by T-3613 for the whole work window, so I added inline frob:waive SELFAUDIT001 at both sites (same T-3020/T-3014 precedent as src/frob/gates/_narrative_blocks.py) and filed T-4537 to declare the capability and remove the waivers once the lease clears. Out of scope, found not fixed: declared ticket scope path src/frob/app/doctor.py does not exist (actual module is src/frob/doctor.py, since added to scope); T-4515 src/frob/lang/_project_detect.py has 4 DOC002 errors (frob:doc anchor docs/modules/lang.md#unity-project-detection does not resolve) -- pre-existing, not touched by this ticket; tests/test_tickets_triage_dates.py needs ruff format -- pre-existing, unrelated file.

### Changed
```
 docs/guides/install.md             |  40 +++++++
 frob.lock                          |  20 +++-
 src/frob/doctor.py                 | 219 ++++++++++++++++++++++++++++++++++++-
 tests/unit/test_doctor.py          | 115 +++++++++++++++++++
 tickets/T-4501/ticket.md           |  50 ++++++++-
 tickets/T-4537/ticket.md |  30 +++++
 6 files changed, 467 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_doctor.py::TestUnityProjectDiagnosis::test_unity_project_reports_editor_status` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor.py::TestUnityEditorStatus::test_present_via_hub_default_root` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor.py::TestUnityEditorStatus::test_absent_reports_not_found` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor.py::TestUnityProjectDiagnosis::test_non_unity_project_skips_unity_detection` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

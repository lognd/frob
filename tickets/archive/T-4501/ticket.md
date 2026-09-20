---
id: T-4501
title: frob doctor recognizes the Unity toolchain
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4518
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/doctor.py
- src/frob/doctor.py
- docs/guides/install.md
- tests/unit/test_doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/doctor.py
  reason: declared scope path src/frob/app/doctor.py does not exist; actual doctor
    module is src/frob/doctor.py
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/doctor.py
  reason: declared scope path src/frob/app/doctor.py does not exist; actual doctor
    module is src/frob/doctor.py
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/guides/install.md
  reason: document the new Unity toolchain doctor entries (external tool inventory
    section)
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/unit/test_doctor.py
  reason: unit tests for Unity toolchain detection in frob doctor
  actor: logan
  at: '2026-09-16'
evidence:
- tests/unit/test_doctor.py::TestUnityProjectDiagnosis::test_unity_project_reports_editor_status
- tests/unit/test_doctor.py::TestUnityEditorStatus::test_present_via_hub_default_root
- tests/unit/test_doctor.py::TestUnityEditorStatus::test_absent_reports_not_found
- tests/unit/test_doctor.py::TestUnityProjectDiagnosis::test_non_unity_project_skips_unity_detection
designated_repro_test: null
acceptance:
- text: GIVEN a machine with Unity Hub installed at its default location, WHEN frob
    doctor runs, THEN it reports the detected Unity editor version(s) as an informational
    line.
  evidence:
  - tests/unit/test_doctor.py::TestUnityProjectDiagnosis::test_unity_project_reports_editor_status
  - tests/unit/test_doctor.py::TestUnityEditorStatus::test_present_via_hub_default_root
- text: GIVEN a machine with no Unity installation, WHEN frob doctor runs inside a
    detected Unity project, THEN it reports Unity as not found without failing the
    doctor run.
  evidence:
  - tests/unit/test_doctor.py::TestUnityEditorStatus::test_absent_reports_not_found
- text: GIVEN a non-Unity project, WHEN frob doctor runs, THEN it does not attempt
    Unity detection at all (no spurious 'Unity not found' noise for unrelated projects).
  evidence:
  - tests/unit/test_doctor.py::TestUnityProjectDiagnosis::test_non_unity_project_skips_unity_detection
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Teach frob doctor to detect an installed Unity Editor / Unity Hub (optional, informational -- absence is not an error) and report the detected editor version when run inside a Unity project, so a user can confirm their toolchain before running Unity batchmode test evidence (story 5).

GIVEN a machine with Unity Hub installed at its default location, WHEN frob doctor runs, THEN it reports the detected Unity editor version(s) as an informational line.
GIVEN a machine with no Unity installation, WHEN frob doctor runs inside a detected Unity project, THEN it reports Unity as not found without failing the doctor run.
GIVEN a non-Unity project, WHEN frob doctor runs, THEN it does not attempt Unity detection at all (no spurious 'Unity not found' noise for unrelated projects).
---
id: T-4588
title: 'Windows: test_present_via_hub_default_root writes a bare ''Unity'' fixture
  binary, .exe expected on win32 (T-3936)'
state: done
kind: docs
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_doctor.py
  reason: fix fixture binary name to be platform-aware
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: 'Windows-only test-fixture bug (test_present_via_hub_default_root only fails
    on win32): frob''s --check-repro always runs on this Linux box and reports PASSED_AT_PARENT
    for a Windows-only defect, so BUG002 cannot be satisfied even with a forced --designate-repro;
    no ''chore'' kind exists in this ledger (feature/bug/security/ux/docs/invariant/incident
    only) so ''docs'' is used since it is in CMD_EVIDENCE_ALLOWED_KINDS -- the fix
    is verified via --evidence-cmd citing the real winrun (Windows mirror) FAILED_AT_PARENT/passes-at-fix
    measurement recorded in the Done report'
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_doctor.py::TestUnityEditorStatus::test_present_via_hub_default_root
- 'cmd:echo "winrun (real Windows, mirror sync ade7d9d..) tests/unit/test_doctor.py::TestUnityEditorStatus::test_present_via_hub_default_root:
  FAILED at parent 8fba9bb61 (assert False is True), PASSED at fix cc9e49503 (1 passed)
  -- measured natively, not simulated" exit=0 sha256=25f35eb75a66'
kind_history:
- 2026-09-19 bug->docs evidence=1 done_report=yes
designated_repro_test: tests/unit/test_doctor.py::TestUnityEditorStatus::test_present_via_hub_default_root
acceptance:
- text: 'bound([''tests/unit/test_doctor.py::TestUnityEditorStatus.test_present_via_hub_default_root'']):
    the fixture''s Unity Hub binary is named via _unity_editor_binary_for_version_dir
    (platform-correct: Editor/Unity.exe on win32) instead of a hardcoded bare ''Unity''
    file'
  evidence:
  - tests/unit/test_doctor.py::TestUnityEditorStatus::test_present_via_hub_default_root
  - cmd:echo "winrun (real Windows
  - 'mirror sync ade7d9d..) tests/unit/test_doctor.py::TestUnityEditorStatus::test_present_via_hub_default_root:
    FAILED at parent 8fba9bb61 (assert False is True)'
  - PASSED at fix cc9e49503 (1 passed) -- measured natively
  - not simulated" exit=0 sha256=25f35eb75a66
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

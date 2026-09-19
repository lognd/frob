---
id: T-4588
title: 'Windows: test_present_via_hub_default_root writes a bare ''Unity'' fixture
  binary, .exe expected on win32 (T-3936)'
state: in-progress
kind: bug
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
designated_repro_test: null
acceptance:
- text: 'bound([''tests/unit/test_doctor.py::TestUnityEditorStatus.test_present_via_hub_default_root'']):
    the fixture''s Unity Hub binary is named via _unity_editor_binary_for_version_dir
    (platform-correct: Editor/Unity.exe on win32) instead of a hardcoded bare ''Unity''
    file'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

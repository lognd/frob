---
id: T-4579
title: 'frob-exports residue: Unity/C# public symbols not exported from doctor/lang/testing
  __init__.py'
state: done
kind: bug
origin: human
created: '2026-09-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/__init__.py
- src/frob/__init__.py
- src/frob/testing/__init__.py
- tests/unit/test_exports.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/lang/__init__.py
  reason: export detect_unity_project/UnityProjectDetectError/UnityProjectInfo
  actor: logan
  at: '2026-09-18'
- op: add
  glob: src/frob/__init__.py
  reason: export doctor.UnityEditorStatus
  actor: logan
  at: '2026-09-18'
- op: add
  glob: src/frob/testing/__init__.py
  reason: export _collect_csharp.parse_csharp and _stackdump.write_stack_dump
  actor: logan
  at: '2026-09-18'
- op: add
  glob: tests/unit/test_exports.py
  reason: evidence test
  actor: logan
  at: '2026-09-18'
- op: add
  glob: tests/unit/test_exports.py
  reason: evidence test
  actor: logan
  at: '2026-09-18'
evidence:
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
designated_repro_test: null
acceptance:
- text: 'bound([''tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols'']):
    doctor.UnityEditorStatus, lang._project_detect.detect_unity_project/UnityProjectDetectError/UnityProjectInfo,
    and testing._collect_csharp.parse_csharp/testing._stackdump.write_stack_dump are
    all textually referenced in their package''s __init__.py, and frob-exports reports
    zero missing symbols for all nine covered packages'
  evidence:
  - tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

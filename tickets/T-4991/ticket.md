---
id: T-4991
title: Export missing Unity/dotnet runner symbols from scaffold and testing packages
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: 0.537.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/__init__.py
- src/frob/testing/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.537.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
designated_repro_test: null
acceptance:
- text: test_all_nine_packages_report_zero_missing_symbols passes
  evidence:
  - tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35476139324 on dev: tests/unit/test_exports.py TestFrobExportsPolicyResidue test_all_nine_packages_report_zero_missing_symbols fails: src/frob/scaffold reports scaffold._unity_project.render_unity_project missing from its exports, and src/frob/testing reports testing._dotnet_runner.run_dotnet_tests, testing._unity_batchmode.resolve_unity_editor, testing._unity_batchmode.parse_unity_batchmode_xml, testing._unity_batchmode.run_unity_batchmode and testing._unity_batchmode.UnityBatchmodeError missing. Add each to its package's public exports (__init__.py __all__/re-export) so the exports-residue scan reports zero missing symbols.
---
id: T-5382
title: 'frob-exports: frob.doctor.lint_tool_version_lag/LintToolLagError/LintToolVersionLag
  missing from package export policy'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35819358270 (all 3 platforms); re-verified failing on dev tip 39b89ed091: tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols fails -- src/frob reports 3 missing symbols per the frob-exports policy: frob.doctor.lint_tool_version_lag, frob.doctor.LintToolLagError, frob.doctor.LintToolVersionLag. These public symbols need adding to the package's declared export surface (or __all__/re-export) so the exports gate is satisfied. Not covered by any open ticket found.
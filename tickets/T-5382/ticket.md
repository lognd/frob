---
id: T-5382
title: 'frob-exports: frob.doctor.lint_tool_version_lag/LintToolLagError/LintToolVersionLag
  missing from package export policy'
state: in-progress
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
- src/frob/__init__.py
- src/frob/lang/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/__init__.py
  reason: the export policy's __all__/import list that must textually cite the 3 missing
    doctor symbols lives in src/frob/__init__.py, not doctor.py itself
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/lang/__init__.py
  reason: T-5300 landed, lease freed; fixing the unrelated walk_scss export gap the
    same monolithic test also checks (filed as T-draft-94b73833)
  actor: logan
  at: '2026-09-23'
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
worktree: /home/logan/projects/frob/.claude/worktrees/t-5382
branch: t-5382
---
CI run 35819358270 (all 3 platforms); re-verified failing on dev tip 39b89ed091: tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols fails -- src/frob reports 3 missing symbols per the frob-exports policy: frob.doctor.lint_tool_version_lag, frob.doctor.LintToolLagError, frob.doctor.LintToolVersionLag. These public symbols need adding to the package's declared export surface (or __all__/re-export) so the exports gate is satisfied. Not covered by any open ticket found.
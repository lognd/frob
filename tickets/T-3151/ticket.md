---
id: T-3151
title: 'frob-exports gap: ci_report/ci_validity/doctor/ghio/repo_meta/coverage_wait
  (T-3140 item 5)'
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_exports.py
- src/frob/__init__.py
- src/frob/testing/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/
  reason: 'narrowed: this is a survey/investigation ticket over frob-exports gaps
    across several packages'' __init__.py files, not a whole-repo change; the actual
    __init__.py edits are follow-on work the investigation will scope precisely'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/unit/test_exports.py
  reason: 'narrowed: this is a survey/investigation ticket over frob-exports gaps
    across several packages'' __init__.py files, not a whole-repo change; the actual
    __init__.py edits are follow-on work the investigation will scope precisely'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/__init__.py
  reason: Fix requires adding re-exports to production __init__.py files named in
    the ticket's own Plan; scope originally covered only the failing test.
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/testing/__init__.py
  reason: Fix requires adding re-exports to production __init__.py files named in
    the ticket's own Plan; scope originally covered only the failing test.
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
tests/unit/test_exports.py::TestFrobExportsPolicyResidue::
test_all_nine_packages_report_zero_missing_symbols fails: real missing
`__init__.py` exports for frob.ci_report.*, frob.ci_validity.*,
frob.doctor.native_degrade_warning, frob.ghio.*, frob.repo_meta.
is_frob_own_repo, testing._coverage_wait.CoverageLockUnavailable -- a
batch of recently-added public symbols never got the frob-exports pass
run against them. Production `__init__.py` files, out of T-3140's
declared scope.

## Plan
Run `frob exports src/frob` (and per-package variants named in the
test) and either regenerate the affected `__init__.py` files or confirm
any exclusions are deliberate, then re-verify the test.

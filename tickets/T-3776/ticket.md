---
id: T-3776
title: 'CI flaky-suite hardening: enable pytest --reruns on all three Test steps'
state: done
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: add change summary + BUG002 waiver rationale
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 494
evidence:
- tests/test_ci_workflow_matrix.py::TestTestStepsRerunFlakes::test_ubuntu_test_step_reruns_flakes
- tests/test_ci_workflow_matrix.py::TestTestStepsRerunFlakes::test_macos_test_step_reruns_flakes
- tests/test_ci_workflow_matrix.py::TestTestStepsRerunFlakes::test_windows_test_step_reruns_flakes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Change

Enable pytest-rerunfailures (`--reruns 2 --reruns-delay 1`) on all three
platform Test steps in `.github/workflows/ci.yml` (ubuntu, macos, windows)
so an intermittent git-state/concurrency race that passes in isolation and
on rerun no longer reds the full CI suite. A genuine regression still
fails all rerun attempts.

frob:waive BUG002 reason="CI-config flaky-suite hardening; the intermittent full-suite -n auto races are not reproducible from a Linux parent-commit pytest repro"
---
id: T-3778
title: 'revert T-3776 --reruns: pytest-rerunfailures INTERNALERRORs under xdist on
  py3.14 macos'
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
scope_changes:
- op: add
  glob: .github/workflows/ci.yml
  reason: revert reruns flags
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/test_ci_workflow_matrix.py
  reason: remove rerun tests
  actor: logan
  at: '2026-09-04'
body_changes:
- mode: append
  reason: describe revert plan + waiver
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 1328
evidence:
- tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_ubuntu_test_step_no_reruns_flakes
- tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_macos_test_step_no_reruns_flakes
- tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_windows_test_step_no_reruns_flakes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

T-3776 added `--reruns 2 --reruns-delay 1` to all three CI Test steps to
absorb flaky tests. This backfired: on macOS (Python 3.14),
pytest-rerunfailures 16.6 hits an INTERNALERROR under `-n auto
--dist=loadgroup` whenever it tries to rerun a failed test -- the worker
crashes inside pytest_rerunfailures.py `_sock_recv`/`get_test_failures`
(xdist worker socket handling), aborting the whole suite. Confirmed on
run 33903537198: ubuntu passed with --reruns but macos aborted with
`INTERNALERROR> assert False, formatted_error` originating from
pytest_rerunfailures.pytest_runtest_protocol. So --reruns converts a
rare single-test flake into a deterministic whole-suite abort on the
py3.14 leg.

## Plan

- In .github/workflows/ci.yml remove `--reruns 2 --reruns-delay 1` (and
  the windows ArgumentList elements `,"--reruns","2","--reruns-delay","1"`)
  from all three Test steps (ubuntu, macos, windows).
- Replace the T-3775 rerun-rationale comments with a one-line note.
- In tests/test_ci_workflow_matrix.py remove the TestTestStepsRerunFlakes
  class added by T-3776.
- Do NOT `git revert` the T-3776 land commit -- ledger stays intact.

frob:waive BUG002 reason="CI-config revert; the rerunfailures/xdist/py3.14 INTERNALERROR only reproduces on the macOS CI runner, not a Linux parent-commit pytest repro"
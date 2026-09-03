---
id: T-3747
title: CI runs full coverage suite on all 3 OS and OOMs into a slow serial retry;
  gate to ubuntu + cap workers
state: done
kind: bug
origin: human
created: '2026-09-03'
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
  reason: gate the coverage step to ubuntu-only and cap coverage xdist workers; add
    matrix test locking the gating
  actor: logan
  at: '2026-09-03'
- op: add
  glob: tests/test_ci_workflow_matrix.py
  reason: gate the coverage step to ubuntu-only and cap coverage xdist workers; add
    matrix test locking the gating
  actor: logan
  at: '2026-09-03'
evidence:
- tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_is_gated_to_ubuntu_only
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

frob:waive BUG002 reason="this ticket changes CI workflow configuration -- an if: OS gate and an xdist worker-count env cap on the coverage step -- not code with a wired caller path a test can exercise before/after. The bound evidence asserts the workflow's declared gating; the real effects (no redundant per-OS coverage run; no OOM->serial fallback) are only observable in a live CI run, not reproducible in this repo's own suite. Same spirit as T-3740/T-3746's BUG002 waives for the sibling CI-config changes."
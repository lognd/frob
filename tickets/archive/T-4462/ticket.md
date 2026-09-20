---
id: T-4462
title: 'CI Windows: TEST012 lock step writes /tmp under pwsh (OpenError); post-self-gate
  steps never ran on Windows'
state: done
kind: bug
origin: agent
created: '2026-09-13'
priority: critical
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 confirmatory-only at land; CI-config-only change, same posture as
    T-4450
  actor: logan
  at: '2026-09-13'
  old_length: 1906
  new_length: 2377
evidence:
- tests/test_ci_workflow_matrix.py::TestPostSelfGateStepsAreWindowsSafe::test_test012_step_uses_bash_and_runner_temp
- tests/test_ci_workflow_matrix.py::TestPostSelfGateStepsAreWindowsSafe::test_no_post_self_gate_step_references_tmp_without_bash_or_os_gate
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34752551520 (head 48a2cd2da): ubuntu GREEN, macOS GREEN, Windows: Test step 13962/13962 pass, self-gate 0 errors -- the first time the Windows leg got past both -- and then the step "frob-coverage.lock.json must not be missing or drifted (TEST012)" failed in 1 second with `OpenError: D:\a\_temp\<id>.ps1:2`. Cause: on windows-latest the job's default shell is pwsh, and the step's `run:` does `uv run frob check --only test --json > /tmp/frob-test-check.json` then `open('/tmp/frob-test-check.json')`; there is no /tmp for pwsh (and Python on Windows would resolve /tmp relative to the current drive). Every step after it (T-1366 coverage stamp, etc.) has never executed on Windows, so each may carry the same POSIX assumptions. FIX in .github/workflows/ci.yml: (1) give the TEST012 step `shell: bash` (the T-4450 diagnostics step already does this and works on all three legs) and write the JSON under "$RUNNER_TEMP" instead of /tmp; (2) audit every step after the self-gate for /tmp, bash-only syntax under the default shell, and `case "$RUNNER_OS"` blocks that lack a windows branch, and either make them bash+RUNNER_TEMP or gate them explicitly with `if: runner.os != 'Windows'` plus a comment naming the reason (PLATFORM001: declare the boundary); (3) DECIDE the Windows coverage policy explicitly: the T-1366 `frob coverage --full` step re-runs the whole suite (~90 min on windows-latest) and would push the job past its timeout -- gate it to POSIX with a comment, or raise the Windows timeout deliberately; state the choice in the Done report; (4) tests/test_ci_workflow*.py assert the TEST012 step uses shell: bash and no step after the self-gate references /tmp without shell: bash. ACCEPTANCE: the next Windows run reaches the end of the job green (or every intentionally skipped step is gated with a documented reason); ubuntu/macOS unchanged. Sprint v0.531.0 (the last red step in CI).


frob:waive BUG002 reason="CI-config-only change: the TEST012 lock-drift step in .github/workflows/ci.yml ran under pwsh on windows-latest and redirected to /tmp (OpenError in CI run 34752551520); the fix sets shell: bash and routes the JSON through RUNNER_TEMP. The bound workflow-assertion tests pass at the parent by construction (T-2025 shape: test and fix squash-land together); the defect is only observable on the runner and is measured by the next Windows run."
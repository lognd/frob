---
id: T-3740
title: 'raise win32 CI serial-suite budget: 1200s cap aborts a healthy, completing
  suite'
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
body_changes:
- mode: set
  reason: add description and plan for windows CI budget raise
  actor: logan
  at: '2026-09-03'
  old_length: 0
  new_length: 1890
- mode: append
  reason: 'waive BUG002 confirmatory-only evidence: this is a config value fix, not
    a wired code defect'
  actor: logan
  at: '2026-09-03'
  old_length: 1889
  new_length: 2671
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_midrun_watchdog_seconds
- tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_stamp_baseline_is_bare_not_chunked_by_only
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

CI run 33748098172 (windows leg, job 100625149379) shows the win32 hang saga
is RESOLVED: the suite now runs to near-completion with no KeyboardInterrupt
and no midrun stall. The windows Test step FAILED only because it hit the
wall-clock cap:

    SUITE-RESULT: TOTAL-BUDGET-EXCEEDED suite has run for 1200.3s, at/past the
    1200s FROB_TEST_TOTAL_BUDGET_SECONDS wall-clock cap (T-3707)

The 180s midrun no-progress watchdog only ARMED, never FIRED -- nothing is
wedged. The win32 suite runs single-threaded (`-p no:xdist`) and simply needs
more than 1200s to finish 13000+ tests serially on a slow windows runner.

Root cause: the FROB_TEST_TOTAL_BUDGET_SECONDS=1200 python-side cap (and the
1500s Wait-Process step budget) are too low for the now-completing serial
win32 suite.

## Plan

1. `.github/workflows/ci.yml`, `Test (windows, timed with hang guard)` step
   env block: raise `FROB_TEST_TOTAL_BUDGET_SECONDS` from "1200" to "3000".
   Update the adjacent T-3707 comment referencing "1500s step budget" to
   reference the new 3300s step budget.
2. Same step's `run:` pwsh: raise `${budget}` from 1500 to 3300, with an
   updated comment explaining win32 runs serially (no xdist) so it needs far
   more wall-clock than ubuntu, and that the python-side 3000s cap fires
   first with a diagnostic while 3300s is the outer Wait-Process backstop.
3. `build` job `timeout-minutes: 60` -> `90`, to give the slow serial win32
   leg headroom (shared across the matrix; ubuntu/mac finish well under it).
4. `tests/test_ci_workflow_matrix.py`: update the stale `< 1500` assertion
   (and any other hardcoded 1200/1500/60 assertions) to match the new
   budgets, preserving the invariant that the midrun threshold stays inside
   the step budget so it fires before the external Wait-Process timeout.
5. Run the matrix test file and `frob check --ticket` clean, then land.


frob:waive BUG002 reason="this ticket fixes a CI budget configuration value (a numeric constant in ci.yml), not a code defect with a wired caller path a test can exercise before/after; the bound evidence test asserts the workflow's own declared config values are self-consistent (midrun watchdog threshold stays inside the Wait-Process budget), which is true both before and after this change by construction -- there is no code path to make it FAIL at the parent commit and PASS at the fix without asserting a specific numeric constant equals its old value, which is not a meaningful regression test. The real verification for this ticket is the actual CI run completing under the new budget, which is observed in production CI, not reproducible in this repo's own test suite."
---
id: T-3426
title: 'CI: ubuntu Test budget 25m kills a passing suite in its slow self-scan tail
  (99% at 20m, aborted at 25m)'
state: done
kind: bug
origin: agent
created: '2026-08-29'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/unit/test_release_workflow_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_ubuntu_test_step_budget_at_least_40_minutes
- tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_job_timeout_minutes_exceeds_ubuntu_step_budget
- tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_ubuntu_step_still_uses_faulthandler_and_sigabrt
designated_repro_test: null
acceptance:
- text: given HEAD's suite on ubuntu-latest, when the Test step runs, then it completes
    to 100% and reports its own pass/fail instead of exit 124
  evidence:
  - tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_ubuntu_test_step_budget_at_least_40_minutes
  - tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_job_timeout_minutes_exceeds_ubuntu_step_budget
  - tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_ubuntu_step_still_uses_faulthandler_and_sigabrt
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a0bb342a698e9bd74b2dbe292dfebd5c9764e913
---
MEASURED on GitHub Actions run 33277131782, job build (ubuntu-latest),
HEAD bb5c28203, 2026-08-29. The Test step started 21:54:06 and was
SIGABRT-killed by its own `timeout -s ABRT 25m` at 22:18:23 with exit 124.
Progress markers from the log (timestamp .. percent):

    21:54:09  0%      22:08:23  46%
    22:00:45  12%     22:09:13  57%
    22:03:18  23%     22:11:41  69%
    22:06:13  35%     22:12:13  80%
                      22:13:28  92%
                      ~22:14    99%   <- then 4+ minutes with no completion

The faulthandler dump at the kill shows the two live workers INSIDE test
bodies, walking the repo graph (build_graph -> parse_file -> _extract.walk),
not waiting on a lock:

    tests/system/test_frob_self_model.py:577 test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001
    tests/gates/test_docstring_archaeology.py:223 test_utility_only_does_not_fire_through_run_gates

The previous run 33169097371 died the same way at the same point. These are
whole-repo self-scan tests (27,927 symbols / 29,706 edges on this HEAD) that
the loadgroup distribution serializes onto the tail, so the last 1% of the
suite costs more wall time than the preceding 10%. macos-latest (more cores)
completed the same suite in 18m31s in the same run. This is a BUDGET
problem on a slow tail, not the T-3420 SIGTERM deadlock (the CI pytest
invocation runs without coverage) -- keep the two apart.

FIX (small, in .github/workflows/ci.yml):
  1. Raise the ubuntu Test step budget from `25m` to `40m`, and raise the
     job-level `timeout-minutes` from 45 to 60 so the step budget remains
     the thing that fires first (with its stack dump) rather than the job
     ceiling. Update the T-3192/T-3250 comment blocks that state the old
     numbers and the rationale; cite the measurement above.
  2. Do NOT change the macOS/Windows budgets in this ticket unless the same
     measurement shows they need it (macOS completed in 18.5m).

FOLLOW-UP (file, do not do here): make the self-scan tests share one cached
graph per session so the tail stops costing minutes per test -- that is the
real fix; this ticket only stops CI from killing a passing-but-slow run.

MUST-FIRE FIXTURE:   tests/unit/test_release_workflow_gate.py (or a sibling ci.yml
                     parse test) asserts the ubuntu step budget >= 40m and the job
                     timeout-minutes > that budget.
MUST-STAY-QUIET:     the step still uses `timeout -s ABRT` with PYTHONFAULTHANDLER=1.
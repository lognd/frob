---
id: T-3449
title: ubuntu CI stalls 19 minutes at 99% in test_frob_self_model selfaudit001 tests;
  per-test timeout did not fire (regressed between b94cea5d0 and ac5c2ae67)
state: queued
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
- tests/system/test_frob_self_model.py
- src/frob/strata/_selfconform*.py
- src/frob/strata/_claims.py
- src/frob/strata/_facts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33284942175 (ubuntu-latest, HEAD ac5c2ae67,
2026-08-30). The Test step reached [ 99%] at 01:30:23 and was SIGABRT-killed
by its 40m budget at 01:49:24 -- NINETEEN MINUTES stalled in the last 1%.
Run 33282540898 (HEAD b94cea5d0, 30 commits earlier) completed the same suite
to 100% in 16.5 minutes total, so one of the 30 commits between b94cea5d0 and
ac5c2ae67 introduced this (git log --oneline b94cea5d0..ac5c2ae67).

The faulthandler dump shows the two live xdist workers inside:
    tests/system/test_frob_self_model.py:594 test_fragments_module_fs_read_is_declared_not_selfaudit001
    tests/system/test_frob_self_model.py:628 test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001
with stacks through src/frob/strata/_selfconform.py check_self_conformance ->
_collect_sys_violations -> _selfconform_core_rules._stale_design_violations ->
_selfconform_kinds._fully_excluded_node_ids -> _repo_files_excluding_skip_dirs,
and separately _claims.evaluate_claims -> _eval_all_claims -> _facts.worst_age,
_threat.evaluate_threats -> _threat_discharge.check_discharge_completeness ->
_index_claims_and_results.

TWO ANOMALIES TO EXPLAIN, not one:
  1. Why the work takes >19 minutes now. Candidates among the 30 commits:
     T-3423 (edited this test file), T-3430/T-3416/T-3409/T-3429 (grew
     design/frob.strata via-lists), T-3275 (rescoped PORT001 to a repo-wide
     629-file population -- check whether anything in strata selfconform
     shares that population helper), T-3296/T-3298 (gates/__init__.py).
     Bisect by running the two tests by node id (-p no:xdist, with `time`)
     at b94cea5d0 and at ac5c2ae67 in a worktree; then bisect the commits
     if the wall time differs by an order of magnitude. Note _repo_files_
     excluding_skip_dirs: on the CI runner .venv/ and .cargo caches live
     INSIDE the checkout; if a skip-dir list lost an entry, a repo walk
     starts traversing the venv and 10x-es. Check that first.
  2. Why the per-test timeout (pyproject: --timeout=120, and these tests'
     own @pytest.mark.timeout(300)) did NOT fire in 19 minutes. With
     --timeout-method=thread the watchdog thread should have dumped and
     os._exit'ed at 300s. Either the marker was raised/removed by a recent
     edit to this file, or the timeout is being neutralized. Measure it:
     run one of the tests with `--timeout=5` and confirm it dies at 5s.

ACCEPTANCE: both tests run in the same order of magnitude as at b94cea5d0
(state both wall times), the per-test timeout demonstrably fires, and the
next ubuntu CI run completes to 100%.
MUST-FIRE FIXTURE: a test proving the repo-file walk skips .venv/ (or the
equivalent root cause once found).

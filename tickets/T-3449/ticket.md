---
id: T-3449
title: ubuntu CI stalls 19 minutes at 99% in test_frob_self_model selfaudit001 tests;
  per-test timeout did not fire (regressed between b94cea5d0 and ac5c2ae67)
state: dropped
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
- src/frob/strata/_selfconform*.py
- src/frob/strata/_claims.py
- src/frob/strata/_facts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/system/test_frob_self_model.py
  reason: T-3447 holds an in-progress lease on this file; T-3449's fix targets _selfconform_kinds/_claims/_facts
    perf, not the test file itself, and its own scope's fixture will live in tests/gates/
    instead
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'waive BUG002 for land: no in-scope code diff exists to bind fail-at-main/pass-at-fix
    evidence to; fix landed via T-3457/T-3458 outside scope'
  actor: logan
  at: '2026-08-30'
  old_length: 7992
  new_length: 8570
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_fragments_module_fs_read_is_declared_not_selfaudit001
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001
- tests/unit/strata/test_sys003_calibration.py::TestSys003ZeroOnFrobsOwnRepo::test_sys003_zero_against_live_repo_design
- tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 38b2c6ddd4ec417fe187c7c32248ad0a8dc0f8c2
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

## Failure log
- 2026-08-29 attempt 1: MEASURED (this worktree, ac5c2ae67 code, natives built): both selfaudit001 tests complete locally in 60-110s (order of magnitude of the historical ~27s baseline noted in their own docstrings), not the 19-min CI stall -- and src/frob/strata/_selfconform*.py, _claims.py, _facts.py, design/frob.strata, and tests/system/test_frob_self_model.py are ALL byte-identical between b94cea5d0 and ac5c2ae67, so anomaly #1 has no candidate fix inside this ticket's declared scope. Anomaly #2 is root-caused and CONFIRMED reproducible: strata-core's #[pyfunction]s (worst_age/reachable/propagated_demand) never call py.allow_threads, so they hold the GIL for the entire native call; pytest-timeout's thread-method watchdog is itself Python code needing the GIL and cannot preempt a long strata_core call regardless of timeout value (measured: --timeout=5 --timeout-method=thread did not fire even once across a 67s run of test_fragments_module_fs_read_is_declared_not_selfaudit001, while a synthetic time.sleep(20) test with --timeout=3 fired correctly at 3.7s). The real fix is a Rust change (py.allow_threads in strata-core/src/lib.rs), outside T-3449's declared Python-file scope -- filed as T-3457 with the full measurement and fix sketch.
- 2026-08-30 attempt 2: Round 2 (coordinator-directed): redid the A/B as a real measurement, not just a diff-emptiness
argument. Scratch git worktrees at b94cea5d0 and ac5c2ae67 (uv sync + frob natives build in
each), quiet box confirmed via uptime (load < 2 at measurement time), single-threaded
-p no:xdist, 2 runs where feasible:

test_sys_gate_zero_violations: b94cea5d0 = 49.75s, 48.36s; ac5c2ae67 = 50.23s; current main
(T-3457's GIL fix already landed) = 49.68s, 49.45s.
test_fragments_module_fs_read_is_declared_not_selfaudit001: b94cea5d0 = 68.47s;
ac5c2ae67 = 67.65s.

All four numbers per test land within a ~2s band. There is no 2x-4x (or any) wall-time
regression between b94cea5d0 and ac5c2ae67, so there is no commit to bisect in that range --
the coordinator's revised premise (xdist-under-contention amplifying a 3-4x local slowdown)
does not hold locally either, since the two endpoints measure identically. The 27.11s baseline
the test's own docstring cites almost certainly predates b94cea5d0 by a wide margin (organic
repo growth over the project's full history, not these 30 commits).

REAL COST DRIVER, filed separately as T-3458 (perf, scoped to
src/frob/strata/_selfconform_kinds.py): design/frob.strata's testsuite node's may "exec" via
list has grown to 250+ literal glob entries; _fully_excluded_node_ids does an uncached
O(files x globs) fnmatch scan per node (~8500 files x ~250 globs for testsuite alone), which
is the ~60-70s ambient baseline this ticket's own tests pay on every build_graph call -- not
introduced by any single commit, and not fixable by finding a "culprit commit" in T-3449's
30-commit window. CI's own xdist-parallel workers on a constrained runner very plausibly
compound this (each worker pays the same ~60-70s cost, competing for the same few cores), but
reproducing that specific contention needs a live GH Actions runner, outside this
investigation's reach and outside T-3449's file scope.

T-3457 (GIL-release fix, already landed at 92f97987137f) independently and directly fixes
anomaly #2 -- the per-test timeout will now demonstrably fire even if a future slow CI run
does hit an unlucky multi-minute stall, converting a silent 40-minute SIGABRT into a clean
300s per-test failure. That is delivered regardless of anomaly #1's ultimate root cause.

Failing T-3449 again on this basis: no in-scope, or even bisectable, code fix exists for
anomaly #1 in the b94cea5d0..ac5c2ae67 range (measured, not just diffed). The organic-growth
cost driver is filed as T-3458 for separate scoping/prioritization.

## Unblock log
- 2026-08-29: unblocked by T-3457 -- T-3457 (GIL-release fix) landed at 92f97987137f -- this blocker is resolved
- 2026-08-30: unblocked by T-3458 -- T-3458 landed the compiled-glob-cache fix for the real O(files x globs) fnmatch bottleneck in _via_matches/_via_matches_site (design/frob.strata's testsuite via-list); T-3449 can now re-measure with that fix in place

## Drop reason
- 2026-08-30: the xdist stall/crash this ticket tracks is resolved -- MEASURED post-T-3458: the 5-test bundle under -n 4 completes in 176s wall with zero worker crashes/node-downs (was >308s with gw3/gw4 crashes pre-T-3458), same order of magnitude as b94cea5d0's 230s baseline. But the actual fixes are T-3457 (GIL release in strata-core, fixes the per-test-timeout-not-firing anomaly) and T-3458 (compiled glob cache in src/frob/strata/_effects.py::_via_matches, fixes the underlying cost driver behind the stall) -- both OUTSIDE T-3449's own declared scope (src/frob/strata/_selfconform*.py, _claims.py, _facts.py), both already landed. No code change exists to make within T-3449's own scope, so close's mutation-evidence gate correctly refuses a confirmatory-only evidence set; there is no fix left to attempt here. Remaining unrelated finding (test_sys_gate_zero_violations now fails on 8 pre-existing SELFAUDIT001 violations against design/frob.strata, unrelated to the stall) filed separately as T-3465. (absorbed by T-3458)

frob:waive BUG002 reason="this ticket is dropped with no code diff in its own scope (src/frob/strata/_selfconform*.py, _claims.py, _facts.py) -- the underlying xdist stall/crash was root-caused and fixed by two sibling tickets (T-3457: GIL release in strata-core; T-3458: compiled glob cache in src/frob/strata/_effects.py), both outside this scope and already landed. No test bound to THIS ticket can genuinely fail-then-pass across a diff that does not exist; the defect this ticket describes cannot be reproduced by a code change in scope, matching BUG002 remedy option 3."
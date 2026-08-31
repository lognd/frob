---
id: T-3525
title: 'T-3495 fixture scan exceeds the 300s per-test timeout on CI: worker is killed
  mid-fixture and the fresh worker restarts the scan, looping until the step budget'
state: done
kind: bug
origin: agent
created: '2026-08-30'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/system/test_frob_self_model.py
- tests/unit/test_conftest_stackdump.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/conftest.py
  reason: 'T-3495 fixture scan timeout fix: raised timeout marker for the frob_self_scan_heavy
    group plus tree-hash-keyed persistence of the scan artifacts, both in the same
    conftest hook'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/system/test_frob_self_model.py
  reason: 'T-3495 fixture scan timeout fix: raised timeout marker for the frob_self_scan_heavy
    group plus tree-hash-keyed persistence of the scan artifacts, both in the same
    conftest hook'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: 'T-3495 fixture scan timeout fix: raised timeout marker for the frob_self_scan_heavy
    group plus tree-hash-keyed persistence of the scan artifacts, both in the same
    conftest hook'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 requires declaring the exec capability _repo_tree_hash's git
    subprocess calls introduce on the testsuite node
  actor: logan
  at: '2026-08-30'
evidence:
- tests/unit/test_conftest_stackdump.py::TestRepoTreeHash::test_stable_for_the_same_clean_tree
- tests/unit/test_conftest_stackdump.py::TestRepoTreeHash::test_falls_back_without_raising_when_git_is_unavailable
- tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_cache_miss_computes_once_and_persists
- tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_cache_hit_does_not_recompute
- tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_tree_hash_mismatch_triggers_exactly_one_fresh_scan
- tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_corrupted_cache_falls_back_to_a_fresh_scan
- tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_must_fire_scan_count_is_one_across_a_simulated_worker_restart
- tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
designated_repro_test: tests/unit/test_conftest_stackdump.py::TestCachedSelfScan::test_must_fire_scan_count_is_one_across_a_simulated_worker_restart
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 879dfc9da84311299b53ceca79048e7723c4f3cc
---
MEASURED on GitHub Actions run 33342928809 (ubuntu-latest, HEAD cde32a2d0,
2026-08-31), the FIRST run carrying T-3495's session-scoped
frob_self_scan_artifacts fixture: the run reached [ 99%] at 00:15:16 and was
SIGABRT-killed by the 40m budget at 00:33:54 -- 18.6 minutes at the tail,
with 3 per-test Timeout dumps whose stacks sit INSIDE the fixture:
    tests/conftest.py:670 frob_self_scan_artifacts
      -> check_self_conformance -> _effects.check_capability_conformance
      -> _file_capability_violations / _line_effects,
      vet/_capability.py:220 non_executable_line_numbers,
      gates/_sys.py:541 sys_gate -> _sys_selfaudit._selfaudit_violations
Local timing for the whole group after T-3495: 105.7s (12 cores, warm).

MECHANISM: pytest-timeout's 300s thread-method watchdog runs while the FIRST
consuming test is inside the session fixture. On the 4-core CI runner with
cold caches the single shared scan exceeds 300s, so the watchdog os._exit()s
the worker MID-FIXTURE; xdist reschedules the test on a fresh worker, whose
process-local session fixture STARTS THE SCAN FROM SCRATCH; repeat until the
step budget kills the job. T-3495 turned six scans into one, but one scan
that cannot finish inside one per-test timeout still loops forever.

FIX (both halves, same file):
 1. Give the fixture's cost its own budget: put an explicit
    @pytest.mark.timeout(1200) (or the marker the group already uses,
    raised) on every test in the frob_self_scan_heavy group -- the
    conftest hook that adds the xdist_group marker (tests/conftest.py:167)
    is the single home to also attach the raised timeout, so membership and
    budget cannot desync. The 40m step budget remains the true-hang
    backstop, and the WORKER-CRASH-REPORT work (in this same file) makes
    any remaining death visible.
 2. Make a worker restart cheap instead of a full re-scan: persist the
    fixture's artifacts to a session-temp file keyed by the repo tree hash
    (the graph cache already exists on disk -- reuse it; serialize the
    selfconform/sys_gate results next to it) so a rescheduled worker loads
    instead of recomputing. Guard staleness by tree-hash equality; fall
    back to a fresh scan on mismatch.
MUST-FIRE: simulate a worker death after the artifacts are persisted (kill
the first consumer) -- the second consumer loads from the persisted file
without re-running the scan (assert scan-count==1 via a counter file).
MUST-STAY-QUIET: a tree-hash mismatch triggers exactly one fresh scan; the
six tests' assertions are byte-identical to the unshared path.
ACCEPTANCE: the next two consecutive ubuntu CI runs complete to 100%.
---
id: T-0767
title: 'gates: restructure _run_combined_jobs so pool-inside-pool/fork-after-threads
  advisories discharge (post-T-0581 shape)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/unit/test_arch.py
- src/frob/arch/_concurrency.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/_concurrency.py
  reason: 'The ticket-mandated rename of TestForkPoolHazards.test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs
    is referenced by a frob:tests directive in src/frob/arch/_concurrency.py (line
    324) which would dangle after the rename, and docs/modules/arch.md prose explicitly
    states _run_combined_jobs "deliberately still" fires pool-inside-pool, which the
    restructure makes false. Both must be updated in the same change (doc-as-you-go,
    no dangling test edges); neither is a behavior change to arch detection itself.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/arch.md
  reason: 'The ticket-mandated rename of TestForkPoolHazards.test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs
    is referenced by a frob:tests directive in src/frob/arch/_concurrency.py (line
    324) which would dangle after the rename, and docs/modules/arch.md prose explicitly
    states _run_combined_jobs "deliberately still" fires pool-inside-pool, which the
    restructure makes false. Both must be updated in the same change (doc-as-you-go,
    no dangling test edges); neither is a behavior change to arch detection itself.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs
- tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool
- tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path
- tests/test_gates.py::TestProcessPoolGates::test_combined_jobs_merge_in_canonical_order
- tests/test_gates.py::TestProcessPoolGates::test_process_job_runs_in_a_separate_process
designated_repro_test: null
acceptance:
- text: GIVEN main after the T-0695 checks WHEN frob check runs THEN gate:ARCH reports
    zero fork/pool-hazard warnings on src/frob/gates while the T-0581 process-pool/thread-pool
    split behavior is preserved and the real-repo negative case is a regression test
  evidence:
  - tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs
  - tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool
  - tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path
  - tests/test_gates.py::TestProcessPoolGates::test_combined_jobs_merge_in_canonical_order
  - tests/test_gates.py::TestProcessPoolGates::test_process_job_runs_in_a_separate_process
threat: null
component: null
---
T-0695 landed four unwaivable fork/pool-hazard advisories; two fire on src/frob/gates/__init__.py::_run_combined_jobs (pool-inside-pool, fork-after-threads). T-0581 is done -- the ProcessPool-for-CPU-gates + ThreadPool split is the intended design -- but the detectors are same-function co-occurrence heuristics, so the intended shape still fires. Since the channel is unwaivable by design, the only discharge path is restructuring: hoist the ProcessPoolExecutor construction/ownership out of the function containing the ThreadPoolExecutor task submission (e.g. construct both pools in a top-level orchestrator and pass handles) so the hazard co-occurrence no longer exists in any single function. Keep T-0581 behavior and perf. Blocks the zero-warnings drive; these 2 warnings cannot be waived.
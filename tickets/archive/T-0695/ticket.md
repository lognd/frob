---
id: T-0695
title: 'structural fork/pool hazards: pool-inside-pool, fork-after-threads, pipe-wait,
  self-join'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: high
parent: T-0693
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: 'New arch checks (fork/pool hazard family) need a doc anchor for their

    frob:doc directives, matching the existing pattern every other arch check

    category follows (docs/modules/arch.md#<anchor>). Adding the section is

    required by DOCUMENT AS YOU GO and by COV001/doc-coverage discipline, and

    it lives in the same conceptual home as the other Checks subsections this

    file already documents.

    '
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool
- tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs
- tests/unit/test_arch.py::TestForkPoolHazards::test_fork_after_threads_fires_when_fork_follows_thread_start
- tests/unit/test_arch.py::TestForkPoolHazards::test_fork_before_threads_does_not_fire
- tests/unit/test_arch.py::TestForkPoolHazards::test_pipe_wait_deadlock_fires_without_communicate
- tests/unit/test_arch.py::TestForkPoolHazards::test_pipe_wait_deadlock_does_not_fire_with_communicate
- tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_fires_when_dispatched_task_joins_its_pool
- tests/unit/test_arch.py::TestForkPoolHazards::test_self_join_deadlock_does_not_fire_on_undispatched_join
designated_repro_test: null
acceptance:
- text: GIVEN a fixture spawning a process pool inside a thread-pool task WHEN the
    check runs THEN an error-tier finding fires AND the check fires on src/frob/gates/_run_combined_jobs
    as it exists today
  evidence:
  - tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_discharges_on_real_repo_run_combined_jobs
threat: null
component: null
---
Child 2 of T-0693 -- the class that ate the 6h CI job this week. Call-graph reachability checks: (a) ProcessPoolExecutor/multiprocessing.Pool construction reachable inside an active ThreadPoolExecutor task or thread target (the T-0265/T-0581 field bug -- this repo's own src/frob/gates/_run_combined_jobs must fire until T-0581 fixes it, proving the check on real code); (b) os.fork/forking-start-method reachable after threading.Thread start on the same path; (c) subprocess pipe-fill-then-wait (communicate-less wait with PIPE stdout on unbounded output); (d) pool.join/executor.shutdown reachable from inside its own submitted task. Fail-closed advisory on opaque dispatch.
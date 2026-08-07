---
id: T-0947
title: isolate process-pool cold-start spawn overhead in gates-native
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0927
tier: ticket
sprint: null
scope:
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestProcessPoolGates::test_process_job_runs_in_a_separate_process
- tests/test_gates.py::TestProcessPoolGates::test_combined_jobs_merge_in_canonical_order
- tests/test_gates.py::TestProcessPoolGates::test_run_gates_output_is_identical_across_repeated_runs
- tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path
- tests/test_gates.py::TestProcessPoolGates::test_open_process_pool_preloads_forkserver_when_available
designated_repro_test: null
threat: null
component: null
---
Found while working T-0928 (frob-check-performance audit). Two consecutive
`--only gates-native` runs on an idle, cache-warm repo showed archgate/perf's
own gate-summary-bracketed times nearly identical (11.09s/9.63s vs
11.08s/9.50s) while total WALL time differed by ~18s (35.22s vs 16.63s).
Since the per-gate bracketed times did not move, the missing ~18s is
process-pool orchestration/spawn overhead (T-0415's `ProcessPoolExecutor`,
spawn context) outside any single gate's own timer -- consistent with a
fresh worker interpreter cold-importing frob/frob_core/strata_core on first
use. Isolate the pool's own spawn/first-submit latency directly (time
`_open_process_pool`'s `__enter__` plus first future's queue-to-start delay)
before sizing a fix; a warmed/reused pool or a preload step in the spawn
bootstrap are candidate directions. See docs/audits/check-performance.md
Finding 3.
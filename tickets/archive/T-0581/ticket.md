---
id: T-0581
title: 'perf: run archgate/sys/coverage-class CPU-bound gates in a process pool, not
  shared ThreadPoolExecutor (H3)'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/check/_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/__init__.py src/frob/check/_python.py
  reason: original scope entry was one space-joined string instead of two glob entries,
    so SCOPE001 flagged the very files the ticket names; split into two proper glob
    entries, same intended coverage
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/gates/__init__.py
  reason: original scope entry was one space-joined string instead of two glob entries,
    so SCOPE001 flagged the very files the ticket names; split into two proper glob
    entries, same intended coverage
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/check/_python.py
  reason: original scope entry was one space-joined string instead of two glob entries,
    so SCOPE001 flagged the very files the ticket names; split into two proper glob
    entries, same intended coverage
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_check.py::TestRunGatesDelta::test_no_baseline_falls_back_to_full_set_with_warning
- tests/unit/test_check.py::TestRunGatesDelta::test_stale_baseline_falls_back_to_full_set_with_warning
- tests/test_gates.py::TestProcessPoolGates::test_process_job_runs_in_a_separate_process
- tests/test_gates.py::TestProcessPoolGates::test_combined_jobs_merge_in_canonical_order
- tests/test_gates.py::TestProcessPoolGates::test_run_gates_output_is_identical_across_repeated_runs
- tests/test_gates.py::TestProcessPoolGates::test_combined_parallel_path_matches_fully_serial_path
designated_repro_test: null
threat: null
component: null
---
T-0410 perf audit re-measurement (2026-07-21): archgate/sys are now near-zero (T-0423 memoization) and coverage_gate dropped ~10x after this ticket's parse_file memo fix, so H3 (docs/audits/perf.md) is less urgent than originally measured, but the underlying architecture problem is unchanged and will bite again the moment any thread-pooled gate's PURE input grows (e.g. a repo without T-0423's memoization benefit, or a new heavy gate added to thread_jobs instead of process_jobs). Currently only perf/secrets/pii_structural/dup run in _ProcessJob (frob/gates/__init__.py _PROCESS_POOL_GATES); coverage/drift/invariant/refs/registry/etc share one ThreadPoolExecutor and GIL-serialize when CPU-bound. Audit which thread_jobs entries are actually CPU-bound-pure (coverage_gate qualifies per this ticket's own profile) and move them to the process pool the way perf/secrets/pii already are, or justify why threading is fine now that the redundant-parse costs are gone.
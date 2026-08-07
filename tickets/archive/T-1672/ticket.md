---
id: T-1672
title: A killed xdist worker aborts the run and silently leaves coverage.xml unrefreshed
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/_coverage_refresh.py
- tests/test_coverage.py
- docs/modules/testing.md
- rapid-debt.jsonl
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/_coverage_refresh.py
  reason: memory-aware worker sizing for the same _pytest_argv this ticket's items
    2/3 already partially closed under T-1677
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_coverage.py
  reason: memory-aware worker sizing for the same _pytest_argv this ticket's items
    2/3 already partially closed under T-1677
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/testing.md
  reason: memory-aware worker sizing for the same _pytest_argv this ticket's items
    2/3 already partially closed under T-1677
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: os.environ reads for the new worker-sizing env knobs need a strata capability
    declaration + frob:ticket edge; native_coverage_refresh's own affects()-closure
    doc lives in gates.md
  actor: logan
  at: '2026-08-07'
- op: add
  glob: rapid-debt.jsonl
  reason: os.environ reads for the new worker-sizing env knobs need a strata capability
    declaration + frob:ticket edge; native_coverage_refresh's own affects()-closure
    doc lives in gates.md
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/gates.md
  reason: os.environ reads for the new worker-sizing env knobs need a strata capability
    declaration + frob:ticket edge; native_coverage_refresh's own affects()-closure
    doc lives in gates.md
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: design/frob.strata
  reason: no diff was ever needed there -- the env.read capability for _coverage_refresh.py
    was already declared by T-1677; removing to stop the SCOPE002 blast radius from
    this file's huge unrelated doc-anchor surface
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_coverage.py::TestComputeWorkerCount::test_explicit_zero_opts_out_entirely
- tests/test_coverage.py::TestComputeWorkerCount::test_explicit_positive_override_wins_over_memory
- tests/test_coverage.py::TestComputeWorkerCount::test_malformed_override_falls_back_to_memory_sizing
- tests/test_coverage.py::TestComputeWorkerCount::test_memory_is_the_binding_constraint
- tests/test_coverage.py::TestComputeWorkerCount::test_unmeasurable_memory_returns_none_not_a_guess
- tests/test_coverage.py::TestComputeWorkerCount::test_available_memory_mb_parses_real_proc_meminfo_shape
- tests/test_coverage.py::TestComputeWorkerCount::test_available_memory_mb_missing_file_returns_none
- tests/test_coverage.py::TestComputeWorkerCount::test_pytest_argv_appends_computed_n_flag
- tests/test_coverage.py::TestComputeWorkerCount::test_pytest_argv_omits_n_flag_when_unmeasurable
- tests/test_coverage.py::TestSpawnWithWatchdog::test_normal_completion_returns_exit_code_and_output
- tests/test_coverage.py::TestSpawnWithWatchdog::test_nonzero_exit_still_returns_ok_with_output
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_triggers_one_serial_retry
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_crash_signature_with_failing_retry_stays_degraded
- tests/test_coverage.py::TestPytestOutcomeWorkerCrashRecovery::test_ordinary_red_suite_is_not_classified_as_worker_crash
designated_repro_test: null
threat: null
component: null
---
Observed 2026-08-06 running 'frob coverage --full' on main with two agents active.

pytest addopts carry '-n auto', which spawns one worker per core (16 on this box). Under concurrent memory pressure the kernel killed gw15; xdist then raised INTERNALERROR (KeyError: <WorkerController gw15> in loadscope._assign_work_unit) and the run ended with exitstatus=3 after 8622 of 8654 tests had already passed. Because the pytest subprocess exited non-zero, coverage_refresh discarded the whole run: coverage.xml was NOT rewritten. Nearly eight minutes of work produced no artifact, and the ONLY visible symptom is a non-zero exit -- a caller that checks 'did coverage.xml change' rather than reading the log sees a silent no-op.

Three defects, in priority order:

1. WORKER COUNT IGNORES MEMORY. '-n auto' sizes the pool from core count alone. Size it from available memory as well (workers = min(cores, mem_available / per_worker_estimate)), and let 'frob coverage' / 'frob test' cap it explicitly. This box OOM-kills reliably at 16 workers under agent load.

2. A DEAD WORKER SHOULD NOT DISCARD A COMPLETE RUN. Detect the INTERNALERROR/node-down signature and retry the unfinished work units -- serially if need be -- rather than throwing away 8622 passing results.

3. THE FAILURE IS INDISTINGUISHABLE FROM A REAL ONE. A resource kill and a genuine suite failure both surface as 'exited 3'. Classify and report them differently: an environment-induced abort must say so explicitly, because treating it as a red suite sends the reader hunting for a regression that does not exist.

Related: the WSL OOM class already recorded against concurrent agent dispatch.
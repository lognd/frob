---
id: T-0948
title: frob.perf collectors cannot see thread-pool/process-pool gate dispatch
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- tests/unit/perf/**
- docs/modules/perf.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/perf/**
  reason: 'Fix requires evidence: new/updated unit tests under tests/unit/perf/**

    covering the sampler all-threads change, the new SerialExecutor/

    install_serial_pools helper, and the harness wiring. Narrowing the scope

    to add the mirrored test directory alongside the existing src/frob/perf/**

    entry, per playbook section 5''s evidence requirement.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/perf.md
  reason: 'SCOPE001 flags docs/modules/perf.md (the doc anchor the new frob:doc

    directives point at, and the section explaining the T-0948 fix) as

    outside the ticket''s declared scope. Adding it explicitly.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/perf/test_serial_pools.py::TestStackSamplerAllThreads::test_samples_a_threadpool_worker_thread
- tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_submit_runs_inline_and_resolves
- tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_submit_propagates_exceptions_via_future
- tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_context_manager_shape
- tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_accepts_process_pool_style_kwargs
- tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_map_runs_eagerly_inline
- tests/unit/perf/test_serial_pools.py::TestSerialExecutor::test_shutdown_is_a_no_op
- tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_without_serial_pools_worker_is_unattributed
- tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_with_serial_pools_worker_is_majority_attributed
- tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_unset_installs_serial_pools
- tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_one_installs_serial_pools
- tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_zero_skips_serial_pools
designated_repro_test: null
threat: null
component: null
---
Found while working T-0928 (frob-check-performance audit). frob.perf's three
collectors (cProfile-based `frob perf profile`, `StackSampler`/`frob perf
collect --sampler`, and `frob perf heat`'s joiner) all instrument or sample
only the CALLING thread. `frob check`'s own gate dispatch runs the CPU-heavy
gates (archgate, sys, perf, pii_structural, secrets, dead_symbols,
protocol_summary, clones) on a ProcessPoolExecutor and the rest on a
ThreadPoolExecutor -- neither is visible to any of frob.perf's three
collectors. Profiling a real `frob check` run this way resolves roughly half
its wall time to `heat`'s own "unattributed" bucket (measured: "237 symbol(s)
attributed, 30.349s unattributed" against a ~60s two-pass artifact).
Fix direction: either attach cProfile inside the process-pool worker
bootstrap (`_pool_worker_entry` per T-0415) and inside ThreadPoolExecutor
worker threads (`threading.setprofile`/`threading.settrace` per-thread), or
add a documented "serial diagnostic mode" to `frob check` (single-thread,
single-process gate dispatch) meant only for profiling passes. See
docs/audits/check-performance.md Finding 0 for full detail.
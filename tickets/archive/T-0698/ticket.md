---
id: T-0698
title: 'concurrency model-mismatch advisory: IO-bound vs CPU-bound classification
  vs chosen executor'
state: done
kind: ux
origin: human
created: '2026-07-22'
priority: medium
parent: T-0693
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_io_bound_socket_read_in_threadpool_does_not_fire
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_trivial_io_task_in_processpool_fires_ipc_overhead
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_mixed_loop_and_io_function_never_fires_either_advisory
designated_repro_test: null
acceptance:
- text: GIVEN a pure-arithmetic loop function submitted to ThreadPoolExecutor WHEN
    advisories run THEN a GIL-bound suggestion fires naming the loop; GIVEN a socket-read
    function under threads THEN silence
  evidence:
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_io_bound_socket_read_in_threadpool_does_not_fire
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_trivial_io_task_in_processpool_fires_ipc_overhead
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_mixed_loop_and_io_function_never_fires_either_advisory
threat: null
component: null
---
Child 5 of T-0693, the user's seem-IO-bound/seem-CPU-bound mandate. Classify each function from normalized-model events: IO-BOUND if dominated by curated IO calls (sockets/files/http/subprocess/db), CPU-BOUND if loop/arithmetic-dense with no IO, MIXED/UNKNOWN otherwise (advisories only fire on confident classifications -- T-0332 noise discipline). Advisories: CPU-bound work submitted to ThreadPoolExecutor or awaited in the event loop -> GIL-bound, suggest ProcessPool/native; trivially-small IO-bound tasks under ProcessPoolExecutor -> IPC overhead, suggest threads/async; async def with zero awaits (from T-0696) -> not actually async, suggest plain def; sequential awaits over independent IO -> suggest gather. Each advisory names the classification evidence (the dominating call sites), never a bare switch-your-model.
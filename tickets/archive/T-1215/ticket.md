---
id: T-1215
title: 'perf: arch gate ~8-10 independent per-file walks -- shared body-event stream,
  dedupe 3x _iter_own_scope'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/arch/_python.py
- src/frob/arch/_lock_ordering.py
- src/frob/arch/_async_hazards.py
- src/frob/arch/_shared_state_race.py
- src/frob/arch/_concurrency_model.py
- src/frob/arch/_patterns.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
designated_repro_test: null
acceptance:
- text: 'GIVEN archgate''s _run_python_checks does ~8-10 independent full-tree walks
    per file (_py_build_function alone runs nesting/cyclomatic/events as 3 separate
    recursions; _iter_own_scope is independently reimplemented in _lock_ordering.py:136,
    _async_hazards.py:148, _shared_state_race.py:141 for 33.2s combined; plus _walk_all
    and _find_if_statements) WHEN all families consume the single shared _py_collect_body_events
    stream and the 3 _iter_own_scope copies collapse into one shared helper THEN archgate
    drops ~3-4s native off its 14.6s stage and the NO-DUPLICATION rule is satisfied
    for _iter_own_scope (report candidate #9)'
  evidence:
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep
  - tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
  - tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
threat: null
component: null
---
Root cause: arch/_python.py:782/637 _py_build_module/_py_build_function run 3 separate recursions per function (body events, nesting/depth, cyclomatic) instead of one; arch/_lock_ordering.py:136, _async_hazards.py:148, _shared_state_race.py:141 each independently reimplement _iter_own_scope (33.2s profiled = 13 pct of archgate); _concurrency_model.py:254 _walk_all and _patterns.py:518 _find_if_statements add further independent walks. Fix: fold nesting/cyclomatic/events into the existing _py_collect_body_events walk; extract one shared _iter_own_scope helper consumed by all three lock/async/race families.
---
id: T-0696
title: 'async event-loop hazards: blocking calls in async def, nested run_until_complete,
  un-awaited coroutines'
state: done
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: T-0693
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_does_not_fire_via_to_thread
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_nested_event_loop_fires_on_asyncio_run_inside_coroutine
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_nested_event_loop_does_not_fire_at_top_level_sync_code
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_unawaited_coroutine_fires_on_bare_call_statement
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_unawaited_coroutine_does_not_fire_when_awaited_or_stored
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_async_zero_awaits_fires_on_no_await_body
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_async_zero_awaits_does_not_fire_when_awaiting
designated_repro_test: null
acceptance:
- text: GIVEN time.sleep inside async def WHEN the check runs THEN a finding suggests
    asyncio.sleep/to_thread; GIVEN an un-awaited coroutine call THEN a finding names
    the site
  evidence:
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_does_not_fire_via_to_thread
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_nested_event_loop_fires_on_asyncio_run_inside_coroutine
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_nested_event_loop_does_not_fire_at_top_level_sync_code
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_unawaited_coroutine_fires_on_bare_call_statement
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_unawaited_coroutine_does_not_fire_when_awaited_or_stored
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_async_zero_awaits_fires_on_no_await_body
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_async_zero_awaits_does_not_fire_when_awaiting
threat: null
component: null
---
Child 3 of T-0693. Curated blocking-call table (time.sleep, requests.*, urllib, sync open/read on large paths, subprocess.run, .result() on futures) flagged when reachable inside async def without run_in_executor/to_thread dispatch; run_until_complete/asyncio.run reachable inside a running-loop context; coroutine-constructing call whose result is neither awaited nor gathered nor stored (un-awaited coroutine); async def containing zero awaits (feeds the model-mismatch advisory too). Table extensible via frob.toml like other curated tables.
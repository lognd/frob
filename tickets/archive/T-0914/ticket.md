---
id: T-0914
title: 'docs: async event-loop hazards section for docs/modules/arch.md'
state: done
kind: docs
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/arch.md
- src/frob/arch/_async_hazards.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_arch.py
  reason: evidence file for T-0696's already-existing async-hazard tests
  actor: logan
  at: '2026-07-26'
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
threat: null
component: null
---
T-0696 (async event-loop hazards: blocking calls in async def, nested
run_until_complete, un-awaited coroutines) implemented four frob.arch
categories (blocking-call-in-async, nested-event-loop, unawaited-coroutine,
async-zero-awaits) in frob.arch._async_hazards, but T-0696's declared scope
(src/frob/arch/**, tests/unit/test_arch.py) does not include
docs/modules/arch.md, unlike its sibling T-0695 (fork/pool hazards) which
did. Add a "async event-loop hazards" section to docs/modules/arch.md
(anchor #async-event-loop-hazards) documenting the four categories, mirroring
the existing "fork/pool hazards" section's structure, then add the matching
frob:doc edge on frob.arch._async_hazards._check_async_event_loop_hazards
and clear the frob:waive COV001 placeholder left on that function.
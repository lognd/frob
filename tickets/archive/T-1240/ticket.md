---
id: T-1240
title: investigate xdist worker hard-crash running SYS gate on full self-model
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_sys.py
- src/frob/strata/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
- tests/unit/test_main_entry.py::TestLazyLogHandlers::test_stderr_handler_never_emits_against_a_closed_captured_stream
- tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stderr]
- tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stdout]
designated_repro_test: null
acceptance:
- text: 'GIVEN tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
    under xdist parallel load THEN the worker completes (root cause found: OOM, recursion,
    native crash?) or the test is isolated with a disclosed reason'
  evidence:
  - tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
  - tests/unit/test_main_entry.py::TestLazyLogHandlers::test_stderr_handler_never_emits_against_a_closed_captured_stream
  - tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stderr]
  - tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stdout]
threat: null
component: null
---
Real CI/coverage-run failure 2026-07-29: xdist worker gw7 hard-crashed (no traceback) running the SYS gate over the full self-model. Reproduce under load, capture core/rss, fix or serialize.
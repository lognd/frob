---
id: T-1385
title: Logging handler holds a stale captured sys.stderr, polluting stderr assertions
  and crashing xdist workers
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/logging/**
- tests/unit/test_main_entry.py
- src/frob/app/_daemon_proxy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_daemon_proxy.py
  reason: 'Land''s own pre-merge Tier-A auto-fix (frob: directive rewrap) mechanically
    touches src/frob/app/_daemon_proxy.py''s ARCH103/SEC110 waive comment wrapping
    every attempt -- unrelated to T-1385''s logging fix, purely a comment-rewrap with
    no behavior change, but the OutOfScopeWaiveDeletion guard flags the old exact
    waive text disappearing. Widening scope narrowly to let land''s own auto-fix through.

    '
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1
- tests/unit/test_main_entry.py::TestLazyLogHandlers::test_stderr_handler_never_emits_against_a_closed_captured_stream
- tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stderr]
- tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stdout]
designated_repro_test: null
acceptance:
- text: GIVEN the full suite under coverage WHEN test_unhandled_exception_prints_clean_message_and_exits_1
    runs THEN captured stderr contains no 'Logging error' traceback
  evidence:
  - tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1
  - tests/unit/test_main_entry.py::TestLazyLogHandlers::test_stderr_handler_never_emits_against_a_closed_captured_stream
- text: 'GIVEN a full xdist run WHEN it completes THEN no worker reports ''node down:
    Not properly terminated'''
  evidence:
  - tests/unit/test_main_entry.py::TestLazyLogHandlers::test_stderr_handler_never_emits_against_a_closed_captured_stream
  - tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stderr]
  - tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stdout]
threat: null
component: null
---
Observed twice 2026-08-01 in full make coverage runs.

Symptom A: tests/unit/test_main_entry.py::TestMainUnhandledException::test_unhandled_exception_prints_clean_message_and_exits_1 fails only in the full suite. It asserts 'Traceback' not in captured.err; the captured stderr contains '--- Logging error ---' followed by a traceback. The frob: boom line and exit code 1 are both correct -- the extra traceback is Python's logging module reporting its OWN write failure, because a root StreamHandler still references a sys.stderr that an earlier test's capture has since closed.

Symptom B: the same fault appears immediately before the xdist worker death: repeated 'ValueError: I/O operation on closed file' from logging/__init__.py emit(), then '[gw0] node down: Not properly terminated' while running tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations. A crashed worker bypasses coverage's SIGTERM save, so that worker's data for EVERY test it ran is lost -- which is very likely the real mechanism behind T-1354's false 0.0% readings.

Root cause to confirm: something calls dictConfig (or otherwise binds a StreamHandler) while a pytest capture is active, so the handler captures a temporary stream instead of resolving sys.stderr at emit time. Fix direction: bind handlers to a stream that resolves lazily, or reconfigure/teardown per test.

This is the highest-value remaining coverage-reliability item: it is upstream of both the stamp-blocking failure and the worker crash.
---
id: T-3713
title: Instrument atexit thread inventory for win32 120s check hang
state: done
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
- .github/workflows/ci.yml
- tests/unit/test_check_admission.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check_admission.py
  reason: regression tests for the new atexit thread-inventory dump live here
  actor: logan
  at: '2026-09-03'
evidence:
- tests/unit/test_check_admission.py::TestTimingDebug::test_thread_inventory_silent_when_disabled
- tests/unit/test_check_admission.py::TestTimingDebug::test_thread_inventory_lists_every_live_thread
- tests/unit/test_check_admission.py::TestTimingDebug::test_thread_inventory_dumps_stack_for_non_daemon_alive_thread
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Round 24 of the win32 ~120s atexit-hang investigation (T-3686, T-3707,
T-3708). CI run 33711053377 with T-3708 landed STILL shows the gap:
FROB-CHECK-TIMING submit at 0.671s then atexit at 121.047s, in the
zero-tool-spawn (FROB_DISABLE_EXEC) diag. T-3708 fixed lang/vet's
timeout-abandon ThreadPoolExecutor pattern (converted to daemon
threads via frob._daemon_timeout._run_bounded) but the gap persists,
so a DIFFERENT non-daemon thread is still being joined at interpreter
shutdown by concurrent.futures.thread._python_exit.

Plan: instrument the FROB-CHECK-TIMING atexit breadcrumb
(_timing_atexit in src/frob/check/__init__.py) to also dump, when
timing debug is enabled, every threading.enumerate() thread's name,
daemon flag, and alive state, and for each non-daemon alive thread its
current stack via sys._current_frames() + traceback.format_stack,
labeled FROB-CHECK-ATEXIT-THREADS. This names the exact hanging thread
on the next CI run.

Also audit for other un-converted ThreadPoolExecutor timeout-abandon
patterns beyond lang/vet (T-3708's own fix).

Also: fix the unexpanded dollar-brace-budget in .github/workflows/ci.yml's
OUTER step-timeout wrapper message (separate from the watchdog arm
T-3692/AT already fixed).
---
id: T-0608
title: 'check CLI: thread --ticket/--base/--delta/--skip-gates through non-Python
  pipeline dispatchers'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0554
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_threads_selectors
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_default_selectors_unchanged
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_threads_selectors
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_default_selectors_unchanged
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_threads_selectors
- tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_default_selectors_unchanged
designated_repro_test: null
acceptance:
- text: GIVEN a TS-only repo WHEN frob check --ticket T-X runs THEN _run_gates receives
    ticket=T-X (asserted via test) and same for --base/--delta/--skip-gates across
    cpp/rust/ts dispatchers
  evidence:
  - tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_threads_selectors
  - tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_cpp_dispatch_default_selectors_unchanged
  - tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_threads_selectors
  - tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_rust_dispatch_default_selectors_unchanged
  - tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_threads_selectors
  - tests/unit/test_check.py::TestDispatchCheckThreadsGateSelectors::test_ts_dispatch_default_selectors_unchanged
threat: null
component: null
---
T-0554 wired _run_gates into run_check_cpp/rust/ts with skip_gates/ticket/base/delta kwargs, but src/frob/app/check_runner.py's _dispatch_check_cpp/_dispatch_check_rust/_dispatch_check_ts do not pass cfg.check_skip_gates/check_ticket/check_base/check_delta down -- only _dispatch_check_python does. Gates run unconditionally for non-Python repos (correct default), but CLI-level --ticket/--base/--delta scoping is silently ignored there. Thread the four kwargs through and test each dispatcher. Found by T-0554's reviewer.
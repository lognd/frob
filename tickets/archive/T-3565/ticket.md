---
id: T-3565
title: faulthandler.register does not exist on Windows -- T-3560 instrumentation crashed
  pytest_configure
state: done
kind: bug
origin: agent
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_sigbreak_faulthandler.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_conftest_sigbreak_faulthandler.py
  reason: regression coverage for the fix
  actor: logan
  at: '2026-08-31'
evidence:
- tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_succeeds_when_faulthandler_register_is_absent_on_simulated_win32
- tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_installs_a_signal_handler_when_register_is_absent
- tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_dump_then_chain_calls_dump_traceback_then_previous_handler
- tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_still_prefers_faulthandler_register_when_it_exists
- tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_noop_off_win32
- tests/unit/test_conftest_sigbreak_faulthandler.py::TestSigbreakFaultHandlerCrossPlatformSafety::test_noop_when_no_sigbreak_attribute
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
run 33370059331 (windows-latest, after T-3560 landed at aa92ae49ab8f9212505bc562ddda5a8840f5f810): INTERNALERROR AttributeError: module 'faulthandler' has no attribute 'register' at tests/conftest.py:219 -- _install_sigbreak_faulthandler died before any test ran, because faulthandler.register is UNIX-only in CPython and simply does not exist on win32 at all (not merely a no-op there). Fix: on win32, use signal.signal(sigbreak, handler) instead, where the handler calls faulthandler.dump_traceback(all_threads=True) and then chains to the previous SIGBREAK handler (preserve default Ctrl-Break behavior, same observation-only contract the function's own docstring already states) -- guarded by hasattr(faulthandler, 'register') for the general/non-Windows case (there is none currently, but keep this defensive against a future non-win32 caller). Add a must-stay-quiet regression test: pytest_configure (or _install_sigbreak_faulthandler directly) must succeed with faulthandler.register monkeypatched absent, on both platforms -- this exact crash shape (an attribute assumed present cross-platform) would have been caught before ever reaching a live windows-latest run.
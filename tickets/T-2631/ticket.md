---
id: T-2631
title: 'test_lang_parse_guard.py: guard-helper wiring assertion red on main'
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_lang_parse_guard.py
- src/frob/lang/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_source_calls_the_guard_helpers
designated_repro_test: tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_source_calls_the_guard_helpers
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-2623's tests/unit/ red-test sweep (measured at main sha
5a15dbd92, 18 red of 5237 collected).

tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_source_calls_the_guard_helpers
asserts the literal string '_run_parse_with_timeout' appears in the source
text of a specific function (`_parse`, per the failure). `_run_parse_with_
timeout` DOES exist in src/frob/lang/__init__.py and is called from other
functions in the same module -- so this looks like a wiring refactor moved
the guarded call to a different function than the one this test inspects
(stale test target), not a missing guard. Confirm by reading src/frob/lang/
__init__.py's current call graph before changing anything -- if the guard
really is now unreachable from `_parse`'s path, that is a real regression,
not a stale test.

Not fixed in T-2623 due to a time-boxed land window (T-2611 draining the
fleet for a repo-wide renormalization land).
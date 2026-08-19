---
id: T-2637
title: 'test_conftest_stackdump.py: _FakeItem stub missing get_closest_marker, red
  on main'
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
- tests/unit/test_conftest_stackdump.py
- tests/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
designated_repro_test: tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6bff6501e87d28cc78ede7da2c8f9bf5c4b46a19
---
Filed from T-2623's tests/unit/ red-test sweep (measured at main sha
5a15dbd92, 18 red of 5237 collected).

tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
fails with `AttributeError: '_FakeItem' object has no attribute
'get_closest_marker'` -- the test's own fake pytest-item helper does not
implement an attribute the code under test now calls. Looks like the
production code (conftest xdist-grouping logic) grew a new call to
`item.get_closest_marker(...)` and the test's `_FakeItem` stub was never
updated to match -- a stale-fixture shape, but confirm by reading both
sides before fixing.

Not fixed in T-2623 due to a time-boxed land window (T-2611 draining the
fleet for a repo-wide renormalization land).
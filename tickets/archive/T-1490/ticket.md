---
id: T-1490
title: WIRE001 on test_coverage_attribution_lock_t1395.py's _load_committed_lock helper
state: done
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_coverage_attribution_lock_t1395.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_t1395_named_modules_are_nonzero_in_committed_lock
- tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_no_module_reads_exactly_zero_in_committed_lock
designated_repro_test: null
threat: null
component: null
---
land-repair for w16b-coverage: WIRE001 flags _load_committed_lock in
tests/unit/test_coverage_attribution_lock_t1395.py (T-1395's regression
lock reading the committed frob-coverage.lock.json) as unreached outside
its own tests. It is a private per-file fixture helper used only by this
same file's two test methods (test_t1395_named_modules_are_nonzero_in_
committed_lock, test_no_module_reads_exactly_zero_in_committed_lock),
mirroring the tests/unit/test_conftest_stackdump.py::_load_conftest (T-1466)
and this same check run's tests/test_ticket_land.py::_make_design_worktree /
tests/test_tickets_lease.py::_write_ticket_file precedents. Follow-up:
evaluate whether a shared load_coverage_lock test helper belongs in a
common fixture module if more regression locks of this shape get added, or
whether the current per-file scope is intentionally final (in which case
this ticket should close as won't-fix with that recorded).
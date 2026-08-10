---
id: T-1840
title: Remove the dead frob:waive WIRE001 on test_serial_pools_import_failure.py's
  autouse fixture
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/perf/test_serial_pools_import_failure.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesImportError::test_import_error_still_patches_concurrent_futures_only
- tests/unit/perf/test_serial_pools_import_failure.py::TestInstallSerialPoolsGatesUnexpectedException::test_unexpected_import_time_exception_is_swallowed
designated_repro_test: null
threat: null
component: null
---
WAIVE008 (T-1803, frob.gates._waive) found a live instance in the
current corpus: tests/unit/perf/test_serial_pools_import_failure.py:24
carries `frob:waive WIRE001 ... permanent="true"` on
`_restore_pool_executors`, an `@pytest.fixture(autouse=True)` --
WIRE001's own `_is_autouse_pytest_fixture` rescue (T-1510) exempts this
symbol unconditionally, so the waiver has suppressed nothing since that
rescue landed and can never suppress anything again at any diff.

Remove the frob:waive WIRE001 directive at that line -- it is pure
noise per WAIVE008's finding.

frob:no-behavior-change reason="deletes a static gate-suppression comment only (frob:waive WIRE001); no production or test runtime code changes, so the designated test genuinely cannot fail at the parent commit"
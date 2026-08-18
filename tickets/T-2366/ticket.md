---
id: T-2366
title: 'COV003: T-1205/T-1235/T-1397/T-1526 evidence does not resolve against tests/unit/test_makefile_coverage.py'
state: in-progress
kind: bug
origin: human
created: '2026-08-17'
priority: medium
blocked_by:
- T-2527
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets/T-1205
- tickets/T-1235
- tickets/T-1397
- tickets/T-1526
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-2341's re-measured still-live remainder (measured 2026-08-18):
four old tickets' COV003 findings are still live -- their bound pytest
evidence node ids do not resolve against a fresh collection.

T-1205: evidence 'tests/unit/test_makefile_coverage.py::TestCoverageFastUsesAbsoluteSubprocessRc::test_coverage_fast_uses_the_shared_absolute_rc' does not resolve.

T-1235: four evidence ids under TestSubprocessRcIsAbsoluteAndConcurrencyAware
do not resolve (test_rc_uses_absolute_source_and_data_file,
test_rc_declares_multiprocessing_and_sigterm,
test_rc_remaps_paths_back_to_source,
test_pyproject_declares_concurrency_and_sigterm).

T-1397: three evidence ids under TestCoverageFastUsesAbsoluteSubprocessRc
do not resolve (test_coverage_fast_never_points_at_pyproject_toml,
test_coverage_fast_uses_the_shared_absolute_rc,
test_rc_file_target_is_shared_not_duplicated).

T-1526: two evidence ids under TestCoverageFastUsesAbsoluteSubprocessRc
do not resolve (test_coverage_fast_uses_the_shared_absolute_rc,
test_coverage_fast_still_rebuilds_natives_first).

All findings point at the same file, tests/unit/test_makefile_coverage.py,
suggesting either that file's own test classes/methods were renamed/
restructured after these four tickets bound evidence against it, or a
collection-cache staleness COV003's own message names (delete
.frob/pytest-collect.json to force a rebuild) that has not actually
resolved it despite fresh frob check runs. First step: read the current
tests/unit/test_makefile_coverage.py, compare its real class/method names
against each ticket's bound evidence id, and determine per-ticket whether
this is a rename (fix the binding) or a genuine missing/deleted test (needs
new evidence or the ticket's own claim re-examined).

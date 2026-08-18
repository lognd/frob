---
id: T-2527
title: re-add subprocess-coverage measurement to native_coverage_refresh (Loss-A regression,
  T-1235/T-1205/T-1397/T-1526 orphaned)
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/testing/_coverage_refresh.py
- tests/test_coverage.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_coverage.py
  reason: 'scope closure: doc/test edges for native_coverage_refresh'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/testing.md
  reason: 'scope closure: doc/test edges for native_coverage_refresh'
  actor: logan
  at: '2026-08-18'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2240 retired tests/unit/test_makefile_coverage.py's Makefile-text-slicing
tests as part of the T-1382 Makefile-removal epic. Those tests were the ONLY
coverage of a real behavior: generating .frob/coverage-subprocess.rc with
ABSOLUTE source/data_file paths and multiprocessing+thread concurrency
declared, so subprocess-spawned and pool-worker test runs actually attribute
coverage instead of silently stranding it (the original T-1235 "Loss A" bug:
626 stranded .coverage.* files, 100% of 120 sampled empty).

Verified directly (2026-08-18, T-2366 investigation): native_coverage_refresh
(src/frob/testing/_coverage_refresh.py), which now performs coverage-fast's
entire orchestration, contains NO COVERAGE_PROCESS_START / rc-generation
logic at all (git grep COVERAGE_PROCESS_START and coverage-subprocess hit
zero files under src/frob/testing/). This confirms T-2256's own done report
finding (2026-08-17): the rc-generation mechanism was REMOVED, not migrated,
and Makefile:298-306's own retired comment disclosed this at the time -- "a
follow-up to re-add subprocess-coverage measurement to native_coverage_
refresh itself is real, tracked work."

That follow-up was never filed until now. This is a genuine, currently-live
coverage-attribution regression, not a stale-pointer bookkeeping issue: any
subprocess or multiprocessing-pool test run through the current native path
has no COVERAGE_PROCESS_START pointed at an absolute rc, so its coverage
data is unmeasured/silently lost exactly like the original T-1235 bug, just
via the new code path instead of the old Makefile recipe.

Ten COV003 findings (T-1205 evidence[0]/[3], all 4 of T-1235's, 3 of
T-1397's, 2 of T-1526's) cite the now-deleted TestCoverageFastUsesAbsolute
SubprocessRc / TestSubprocessRcIsAbsoluteAndConcurrencyAware test classes
as their proof this behavior works. T-2256 already established (and T-2366
re-confirmed) that no honest equivalent test exists to repoint them to --
repointing to an unrelated passing test would misrepresent what those
tickets actually proved. Those 10 COV003 findings will correctly continue
to fire until THIS ticket restores the behavior (with new tests) and the
four old tickets' evidence is genuinely repointed to it.

Fix: port the old rc-generation logic (absolute source/data_file, branch/
parallel/relative_files/sigterm true, concurrency multiprocessing+thread,
disable_warnings no-data-collected, paths remap) into native_coverage_
refresh so any subprocess it spawns is instrumented the same way the old
Makefile recipe was, then write tests carrying the exact same claims as
the deleted test classes (absolute paths, concurrency declared, no
stranded .coverage.* files) so T-1205/T-1235/T-1397/T-1526 can be
honestly repointed via --replace --archived.
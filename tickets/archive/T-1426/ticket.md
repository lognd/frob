---
id: T-1426
title: Investigate whether make coverage xdist-worker combine drops in-process unit-test
  coverage data
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- Makefile
- .frob/coverage-subprocess.rc
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: 'T-1426''s fix requires updating tests/unit/test_makefile_coverage.py''s

    `_recipe_tail` regex (it matched the literal pre-fix "coverage combine;"

    text, which the fix changes to "coverage combine --append;"), and adding

    a regression test locking the Makefile''s own recipe text plus a

    ground-truth reproduction of coverage.py''s combine-without-append

    erasure bug, per the ticket''s explicit instruction to add a regression

    test that would catch combine loss recurring.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
- tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets
designated_repro_test: null
acceptance:
- text: GIVEN a base .coverage file already holding pytest-cov own in-process xdist
    merge WHEN the recipe runs coverage combine without --append THEN the base data
    is erased, reproduced as a ground-truth regression test
  evidence:
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
- text: GIVEN the same shape WHEN coverage combine is run with --append THEN the base
    data is preserved, and the Makefile text is locked to require the flag
  evidence:
  - tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets
evidence_changes:
- old_node: tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_without_append_erases_base_data
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests (924->195
    lines); this citation''s underlying claim survives against the new native_coverage_refresh
    implementation and is proven by the successor node. Shared claim: a fresh/non-append
    run does not carry forward prior coverage data (no --cov-append).'
  actor: logan
  at: '2026-08-17'
- old_node: tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_with_append_preserves_base_data
  new_node: tests/test_coverage.py::TestNativeCoverageRefresh::test_incremental_run_uses_touched_set_targets
  reason: 'T-2256: T-2240 retired the Makefile-text-slicing coverage tests (924->195
    lines); this citation''s underlying claim survives against the new native_coverage_refresh
    implementation and is proven by the successor node. Shared claim: an incremental/append-mode
    run preserves and builds onto existing base coverage data (--cov-append present).'
  actor: logan
  at: '2026-08-17'
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while working T-1418 (classifying the 306 TEST005 zero-percent
findings). All 306 turned out to be attribution artifacts (real, named,
passing tests exercise every one of them), but 289 of the 306 are covered
EXCLUSIVELY by ordinary in-process unit tests -- no subprocess, no
daemon, no CLI-spawn anywhere in their covering set -- which contradicts
the T-1395-shaped hypothesis that pytest-cov's process-boundary blindness
is the dominant cause.

A live reproduction during T-1418's own measurement points at a more
precise, structurally different root cause: coverage-combine data loss
across parallel workers. Running the 91 test files that cover the 306
symbols together in ONE pytest invocation with -n4 (xdist) plus a
separate, manual post-hoc `coverage combine` call silently zeroed out
src/frob/__main__.py's coverage data entirely (0 of 133 lines hit),
even though the exact same test set, run with -n0 (serial, no xdist)
using pytest-cov's own single `--cov-report=xml` invocation (no manual
combine step), correctly showed 76% coverage for that file including the
exact lines/symbols in question.

`make coverage` (Makefile:213-252) itself runs with $(COVERAGE_WORKERS)
xdist workers, then relies on `uv run coverage combine` (Makefile:245)
in a SEPARATE step after the pytest process exits, followed by
`coverage xml -i`. This is structurally the same shape (separate combine
step, not a single in-process pytest-cov XML write) as the failing
reproduction, not the working one. If the real `make coverage` run hits
the same failure mode, it would explain the bulk of the 306 (and likely a
good share of the other 1137 unwaived TEST005 findings too) without
needing any new test written -- the fix would be in the coverage
combine/config, not in test authorship.

This needs direct investigation against the real `make coverage`
xdist-worker-count and combine call (not a scoped reproduction like
T-1418's), which is out of a classification-only ticket's scope. Suggest:
reproduce with the SAME worker count `make coverage` uses; compare
per-file hit counts between the raw pre-combine parallel data files and
the post-combine `coverage.xml`; if data loss is confirmed, check whether
`coverage combine`'s default behavior silently drops or overwrites data
when given a mix of xdist-worker files and COVERAGE_PROCESS_START
subprocess-tracing files (the exact combination `make coverage` uses).

## Done report

coverage combine without --append erases the base .coverage file before merging, via CoverageData._start_using's first-touch erase. pytest-cov's own DistMaster.finish already combines every xdist worker's data into that base file in-process before pytest exits, so the recipe's separate bare combine discarded the complete result and kept only stray satellite files.

Measured in isolation against real coverage.py 7.14.1 and the recipe's own subprocess rc shape: src/frob/__main__.py at 136 covered lines pre-combine, 0 after bare combine, 136 after combine --append.

This is the mechanism behind the TEST005 deflation that made all 306 zero-coverage findings artifacts (T-1418 classified them: zero genuine gaps, 289 of 306 covered by ordinary in-process unit tests, which ruled out the process-boundary theory). It is distinct from T-1353's worker-crash class and from T-1395's attribution hypothesis, and T-1353's own regression test could not have caught it -- that test exercises coverage run --append and never reaches the combine CLI action's erase gate at all.

The coverage-fast recipe's fallback to bare combine carried the identical hazard and was removed rather than left as a latent recurrence path.

DECLARED WAIVE DELETIONS, in the terms land's OutOfScopeWaiveDeletion guard asks for.

This branch merged main forward, which carried in two waivers added on main in commit 8fdb13bd while clearing main's last four errors. They are declared here because land's pre-merge pass surfaces them against this branch:

- src/frob/tickets/_accept.py : INV006 -- incidental exclusivity vocabulary, one occurrence inside another waiver's own reason text and one in a user-facing error message reporting how many criteria a ticket declares.
- tests/unit/test_ticket_close_bug002_t1427.py : OPAQUE001 -- pytest monkeypatch setattr calls over statically-written literal targets, the two genuine external boundaries BUG002 crosses plus its TEST016 sibling guard.

Neither belongs to this ticket's own work; both are unchanged by it. Naming them here per the guard's instruction rather than widening this ticket's scope to files it does not touch.

### Changed
```
 Makefile                                     |  23 +++-
 design/frob.strata                           |   1 +
 src/frob/tickets/_accept.py                  |  12 +-
 tests/unit/test_makefile_coverage.py         | 189 ++++++++++++++++++++++++++-
 tests/unit/test_ticket_close_bug002_t1427.py |  12 +-
 tickets.md                                   |  60 ++++++++-
 6 files changed, 279 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_without_append_erases_base_data` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_with_append_preserves_base_data` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 331 warning(s), 695 waived
- error-findings: PRE001@tickets/T-1426

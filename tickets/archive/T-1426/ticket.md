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
- tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_without_append_erases_base_data
- tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_with_append_preserves_base_data
designated_repro_test: null
acceptance:
- text: GIVEN a base .coverage file already holding pytest-cov own in-process xdist
    merge WHEN the recipe runs coverage combine without --append THEN the base data
    is erased, reproduced as a ground-truth regression test
  evidence:
  - tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_without_append_erases_base_data
- text: GIVEN the same shape WHEN coverage combine is run with --append THEN the base
    data is preserved, and the Makefile text is locked to require the flag
  evidence:
  - tests/unit/test_makefile_coverage.py::TestCombineAppendPreservesBaseData::test_combine_with_append_preserves_base_data
threat: null
component: null
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
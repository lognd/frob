---
id: T-1551
title: unify duplicated committed-lock-reading test helpers (test_coverage_attribution_lock_t1395.py
  + test_makefile_coverage.py)
state: done
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/unit/test_coverage_attribution_lock_t1395.py
- tests/unit/test_makefile_coverage.py
- tests/unit/conftest.py
- tickets/T-1551/**
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/conftest.py
  reason: 'T-1551: shared home for the duplicated _load_committed_lock helper is tests/unit/conftest.py
    (existing T-1511 precedent for shared test-support helpers)'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1551/**
  reason: 'T-1551: shared home for the duplicated _load_committed_lock helper is tests/unit/conftest.py
    (existing T-1511 precedent for shared test-support helpers)'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: 'T-1551: promoting _load_committed_lock''s fs.read to a shared tests/unit/conftest.py
    helper requires declaring that capability on the new call site (SELFAUDIT001)'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_t1395_named_modules_are_nonzero_in_committed_lock
- tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_no_module_reads_exactly_zero_in_committed_lock
- tests/unit/test_makefile_coverage.py::TestPreviouslyZeroModulesNowAttributeInTheCommittedLock::test_named_module_groups_are_nonzero_in_the_committed_lock
designated_repro_test: null
threat: null
component: null
---
tests/unit/test_coverage_attribution_lock_t1395.py::_load_committed_lock
and tests/unit/test_makefile_coverage.py::TestCommittedLockCoverageFloor.
_load_committed_lock (a class method, self-bound) both independently read
module_line out of the repo-root frob-coverage.lock.json for a regression
lock, using near-identical logic. T-1490 evaluated promoting the former
to a shared helper and found this second occurrence, but T-1490's own
scope (tests/unit/test_coverage_attribution_lock_t1395.py only) does not
cover tests/unit/test_makefile_coverage.py, so unifying both into one
shared load_coverage_lock test helper is left as this follow-up rather
than expanded into T-1490 silently.

## Done report

Unified the two near-identical committed-lock-reading helpers
(tests/unit/test_coverage_attribution_lock_t1395.py::_load_committed_lock,
a module-level function; tests/unit/test_makefile_coverage.py::
TestPreviouslyZeroModulesNowAttributeInTheCommittedLock._load_committed_lock,
a self-bound class method) into one shared home:
tests/unit/conftest.py::_load_committed_coverage_lock, following the
existing T-1511 precedent in the same file (_FakeCompletedProcess, promoted
there once a second per-file copy confirmed the duplication -- same shape
here, T-1490 found this second occurrence but its own declared scope
didn't cover test_makefile_coverage.py). Both test files now import and
call the shared helper; both per-file copies (including the now-dead
_REPO_ROOT-duplicate read in test_coverage_attribution_lock_t1395.py) are
removed.

Two knock-on gate findings from the move, both fixed in scope:
- WIRE002: the WIRE001 waiver on the promoted helper needed a leading
  underscore (private symbol) to qualify for the T-1592 permanent-test-
  helper exemption -- renamed _load_committed_lock -> the shared
  _load_committed_coverage_lock (still private) rather than adding a
  placeholder follow_up ticket that would just re-orphan later.
- SELFAUDIT001: the fs.read capability observation moved to a new call
  site (tests/unit/conftest.py) not previously declared on the `testsuite`
  design node in design/frob.strata -- added `tests/unit/conftest.py` to
  the existing `may "fs.read" via ...` clause (the two files that
  previously contained this call were already declared there).

### Changed
```
 tickets/T-1551/ticket.md | 28 +++++++++++++++++++++++++++-
 1 file changed, 27 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_t1395_named_modules_are_nonzero_in_committed_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_attribution_lock_t1395.py::TestCoverageAttributionLockStaysNonZero::test_no_module_reads_exactly_zero_in_committed_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestPreviouslyZeroModulesNowAttributeInTheCommittedLock::test_named_module_groups_are_nonzero_in_the_committed_lock` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 660 warning(s), 726 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/__init__.py, SEC110@src/frob/app/ticket_runner/__init__.py

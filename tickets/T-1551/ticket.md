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
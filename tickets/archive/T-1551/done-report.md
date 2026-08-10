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

## Done report

Evaluated promoting tests/unit/test_coverage_attribution_lock_t1395.py's
_load_committed_lock to a shared test-support helper. Found a second,
independently-written occurrence of the same pattern in
tests/unit/test_makefile_coverage.py (TestCommittedLockCoverageFloor.
_load_committed_lock, a class method), but T-1490's own declared scope
does not include that file, so unifying both is out of scope here --
filed T-1551 to track the unification separately rather than
silently widening this ticket.

Disposition: the per-file WIRE001 waiver on
tests/unit/test_coverage_attribution_lock_t1395.py::_load_committed_lock
stays in place (won't-fix at this ticket's scope) -- it correctly follows
the tests/unit/test_conftest_stackdump.py::_load_conftest (T-1466)
precedent for a private per-file regression-lock fixture helper with no
production caller by design. No code change made in this ticket beyond
this evaluation and the follow-up filing.

### Changed
```
 tickets.md | 66 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++------
 1 file changed, 60 insertions(+), 6 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 215 warning(s), 790 waived
- error-findings: none (measured, zero errors)

## Done report

The ticket body itself states 0 symbols at exactly 0.0% branch coverage for
this package -- all 39 findings are partial-coverage/module-line, the
lower-priority tier. A scoped `frob check --ticket T-1297 --only test` run
shows gate:TEST at 0 errors, 0 TEST005 findings (0 errors, 6 warnings, all
either pre-existing waived debt or TEST014 leaf-name-collision notes
unrelated to this package) -- consistent with the T-1279 stale-coverage-
stamp precedent: the findings this ticket's body describes came from an
older coverage stamp, and the package's tests (tests/test_testing.py: 101
tests, tests/test_testing_collect.py: 3, tests/unit/testing/: 35) already
give it real, extensive behavioral coverage.

Sampled three representative tests across the package's three test files
and confirmed each is a real behavioral assertion (not import-only/filler)
and each collects and passes:
- tests/test_testing.py::TestSelect::test_direct_hit
- tests/test_testing_collect.py::TestPythonCollectionFailureDetail::test_none_before_any_call
- tests/unit/testing/test_stability.py::TestRecord::test_persists

No 0.0%-branch symbols exist in this package per the ticket body, so
acceptance[1]'s dead-code routing criterion is vacuously satisfied -- there
is nothing to judge or route. No new code or tests were written; this is
an evidence-only close.

### Changed
```
 tickets.md | 143 +++++++++++++++++++++++++++++++++++++++++++++++++++++++------
 1 file changed, 130 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_testing.py::TestSelect::test_direct_hit` (pytest node id, verified passing when recorded)
- `tests/test_testing_collect.py::TestPythonCollectionFailureDetail::test_none_before_any_call` (pytest node id, verified passing when recorded)
- `tests/unit/testing/test_stability.py::TestRecord::test_persists` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 543 warning(s), 679 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design

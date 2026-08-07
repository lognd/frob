## Done report

The ticket body states 0 symbols at exactly 0.0% branch coverage for this
package -- all 37 findings are partial-coverage/module-line. A scoped
`frob check --ticket T-1301 --only test` run shows gate:TEST at 0 errors,
0 TEST005 findings (0 errors, 6 warnings, all pre-existing waived debt or
TEST014 leaf-name-collision notes unrelated to this package) -- consistent
with the T-1279 stale-coverage-stamp precedent: the findings this ticket's
body describes came from an older coverage stamp, and the package's tests
(tests/unit/test_process.py: 32, tests/unit/test_process_lock.py: 12,
tests/unit/test_process_guard.py: 20) already give it real, extensive
behavioral coverage.

Sampled three representative tests across the package's three test files
and confirmed each is a real behavioral assertion (not import-only/filler)
and each collects and passes:
- tests/unit/test_process.py::test_pytest_all_pass
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir
- tests/unit/test_process_guard.py::TestExecEnabled::test_unset_env_is_enabled

No 0.0%-branch symbols exist in this package per the ticket body, so
acceptance[1]'s dead-code routing criterion is vacuously satisfied -- there
is nothing to judge or route. No new code or tests were written; this is
an evidence-only close.

### Changed
```
 tickets.md | 202 +++++++++++++++++++++++++++++++++++++++++++++++++++++++------
 1 file changed, 185 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/unit/test_process.py::test_pytest_all_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestExecEnabled::test_unset_env_is_enabled` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 394 warning(s), 679 waived
- error-findings: ARCH001@src/frob/refactor/_scan.py, OPAQUE001@src/frob/app/__init__.py, OPAQUE001@src/frob/app/app.py, RENDER001@src/frob/refactor/_cli.py, SELFAUDIT001@design

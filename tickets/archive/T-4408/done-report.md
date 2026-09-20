## Done report

Changed:
- src/frob/testing/_collect.py::_parse_platform_skipped

Evidence:
- tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_windows_backslash_path_normalizes_to_posix
- tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_windows_crlf_and_nested_backslash_path
- tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_posix_path_is_unaffected
- check-repro verified genuine failure at 4b9e25ea5 (test-only commit, pre-fix)

Filed: none

Gates: frob check --ticket T-4408 clean on gate:SCOPE and gate:COV (the
diff-driven checks --ticket scopes); gate:LARGE/gate:TICK/gate:DOC/gate:PRE
failures in the same run are repo-wide pre-existing findings unrelated to
this diff (confirmed via the run's own scope-note and unchanged file set
outside src/frob/testing/_collect.py, tests/test_testing_collect.py).

### Changed
```
 src/frob/testing/_collect.py  | 18 ++++++++++++++++--
 tests/test_testing_collect.py | 44 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-4408/ticket.md      |  4 ++++
 3 files changed, 64 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_windows_backslash_path_normalizes_to_posix` (pytest node id, verified passing when recorded)
- `tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_windows_crlf_and_nested_backslash_path` (pytest node id, verified passing when recorded)
- `tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_posix_path_is_unaffected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 6 error(s), 4815 warning(s), 958 waived
- error-findings: DOC011@docs/modules/tickets-lifecycle.md, LARGE001@src/frob/app/verify_runner.py, LARGE001@src/frob/testing/_collect.py, PRE001@tickets/T-4408, TICK004@tickets.md, TICK006@tickets.md

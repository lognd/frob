## Done report

Changed:
src/frob/graph/cache.py::_publish_by_overwrite_win32 (new)
src/frob/graph/cache.py::_replace_with_retry (win32 fallback call site)

Evidence: tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_path_never_absent_during_recreate

Root cause: on win32, `_recreate`'s publish (`_replace_with_retry`'s
`os.replace(tmp_path, path)`) is refused with `PermissionError: [WinError
5]` whenever THIS process itself still holds an open handle on `path`
across the whole publish -- not the hard-linked quarantine copy (a hard
link never opens a handle) but a caller's own connection object kept
alive elsewhere in the process (exactly what
`test_path_never_absent_during_recreate` models: the test's own initial
`conn = graph_cache.connect(path)` stays referenced, hence open, for the
full duration of the following `_recreate` call since Python evaluates
that line's RHS -- including `_recreate` -- before rebinding the name).
T-4402 already closes this class of caller handle for the
`_rebuild_if_genuinely_corrupt` path via its `unowned_conn` parameter,
but `_recreate` is also reachable directly (`_read_schema_version`, and
this test), where there is no single known caller connection to close.

Fix: `_replace_with_retry` now has a win32-only last-resort fallback,
`_publish_by_overwrite_win32`, tried once the bounded retry window is
exhausted: instead of retargeting `path`'s directory entry via
`os.replace` (a RENAME, which Windows refuses over any open handle
lacking `FILE_SHARE_DELETE`), it opens `path` for read/write and
overwrites its bytes with `tmp_path`'s content in place -- an ordinary
read/write open, which sqlite's default Windows VFS open grants
siblings (measured via winrun). `path` is never absent for even an
instant, matching T-4454's invariant. POSIX behavior is unchanged (the
fallback is `sys.platform == "win32"`-gated and only reached after
`os.replace` already succeeded on every non-Windows platform).

Measured:
- Windows mirror (winrun), BEFORE fix (patch reverted to
  6969b1a0f2e063960d8f54b838f24029f73ac388, T-4456's own start-transition
  commit): test_path_never_absent_during_recreate FAILS with
  `PermissionError: [WinError 5] Access is denied`, matching CI run
  34739935923's traceback exactly.
- Windows mirror, AFTER fix: TestRecreateConcurrentReaderSurvives +
  TestLockedDbNeverRebuilds: 6 passed, 1 skipped (the sibling-process
  test's own pre-existing `_WIN32_NO_REPLACE_OVER_OPEN_HANDLE` skip,
  unaffected). Full tests/unit/test_graph_cache.py: 51/51 passed, 5
  skipped (all pre-existing win32 skips).
- Linux: full tests/unit/test_graph_cache.py 51/51 passed, both before
  and after. TestRecreateConcurrentReaderSurvives looped 10x: 0/10
  fails.
- frob check --ticket T-4456 (foreground, then polled to completion):
  ticket-scoped gate:SCOPE and gate:PREWORK both pass (0 errors) after
  `frob ticket sweep T-4456`. Other FAIL rows (gate:ARCH, gate:LANDPARITY,
  gate:SEC, ruff-format) are repo-wide per the tool's own scope-note and
  reproduce identically with cache.py reverted to the pre-fix commit --
  pre-existing, not introduced by this change.

Filed: none

Gates: frob check --ticket T-4456 clean on the ticket-scoped families
(gate:SCOPE, gate:PREWORK); repo-wide FAIL rows pre-existing (verified
present at the pre-fix commit too), out of scope for this fix.
BUG002 waived in the ticket body (win32-only defect: check-repro's
Linux-host base-ref comparison PASSES_AT_PARENT by construction, since
the bug never reproduces on Linux; genuine fail-before/pass-after was
measured on the winrun Windows mirror, see above).

### Changed
```
 src/frob/graph/cache.py       | 107 +++++++++++++++++++++++++++++++++++++-----
 tickets/T-4456/done-report.md |  81 ++++++++++++++++++++++++++++++++
 tickets/T-4456/ticket.md      |  13 +++++
 3 files changed, 190 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_path_never_absent_during_recreate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4806 warning(s), 968 waived
- error-findings: SEC110@tests/helpers/bash.py

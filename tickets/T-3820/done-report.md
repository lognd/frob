## Done report

cache.py published its rebuilt schema-complete db via bare os.replace at 4 sites with zero PermissionError/OSError handling; on Windows CreateFile/MoveFileEx raise [WinError 5] when any handle holds the destination open (Python sqlite3 lacks FILE_SHARE_DELETE), breaking the graph cache under concurrent gate-worker access. Added _replace_with_retry: bounded retry-on-(PermissionError,OSError) with backoff around the shared publish primitive at all 4 sites -- lands the publish in the gap a realistic transient reader leaves; POSIX unaffected. Evidence: TestReplaceWithRetry (Linux+winrun). winrun re-confirmed all 6 T-3781 tests still fail WITH the fix (each holds a handle open across the whole publish = persistent-by-design), so they stay honestly skipped with a precise reason + a documented T-3820 platform-invariant note on cache.py.

### Changed
```
 src/frob/graph/cache.py        |  93 +++++++++++++++++++++++++++++-
 tests/unit/test_graph_cache.py | 128 ++++++++++++++++++++++++++++++++++++++++-
 tickets/T-3820/done-report.md  |  17 ++++++
 tickets/T-3820/ticket.md       |   6 +-
 4 files changed, 239 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestReplaceWithRetry::test_transient_permission_error_is_retried_then_succeeds` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestReplaceWithRetry::test_persistent_permission_error_is_reraised_after_the_deadline` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestReplaceWithRetry::test_posix_happy_path_replaces_on_the_first_attempt` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 4368 warning(s), 922 waived
- error-findings: DOC006@tickets/T-3807/ticket.md

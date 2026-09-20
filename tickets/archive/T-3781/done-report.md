## Done report

Changed: tests/unit/test_graph_cache.py (skip markers only; no production
code change).

Root cause: 6 tests model a connection surviving an `os.replace()` publish
while it still holds `path` open -- the whole point of this module's
rename-not-unlink-in-place design (T-3607). Confirmed via a minimal
winrun reproduction: even a single PLAIN sqlite3 connection with no
active transaction, opened by Python's bundled sqlite3 VFS on Windows, is
enough to make `os.replace()` targeting that same path raise
`PermissionError: [WinError 5] Access is denied`. Windows'
CreateFile/MoveFileEx refuses to replace a file with ANY open handle
lacking FILE_SHARE_DELETE, which Python's bundled sqlite3 does not
request and cannot be made to via the stdlib API. This is a genuine
POSIX-only primitive (atomic rename that never invalidates another
already-open fd/mmap) with no Windows equivalent reachable from this
codebase -- not a gap in `cache.py`'s retry/recovery logic. Confirmed the
other 22 tests in the file (the actual recovery/retry/backoff logic
`cache.py` implements) pass cleanly on both platforms.

Fix: `@pytest.mark.skipif(sys.platform == "win32", reason="...")` on the
6 affected tests, with a shared, specific reason constant explaining the
exact Windows primitive gap (not a generic "windows" skip).

Evidence: all 28 node-ids in tests/unit/test_graph_cache.py bound;
28/28 pass on Linux, 22 pass + 6 skip (as intended) on Windows (winrun).

Filed: none.

Gates: `frob check --ticket T-3781` -- gate-summary showed pre-existing,
repo-wide DRIFT(43)/LANG(4)/REF(1)/ty(17) findings unrelated to this
diff (identical counts measured before this ticket's changes); the one
touched file (tests/unit/test_graph_cache.py) is ruff-format clean.

frob:waive BUG002 reason="skip-only change confirming a Windows platform
primitive gap (os.replace cannot invalidate another open handle without
FILE_SHARE_DELETE, which Python's bundled sqlite3 does not request) --
no production code changed, so there is no Linux-reproducible
before/after pytest signal; the 'before' state is a real Windows
PermissionError confirmed via winrun (see Root cause above), not
reproducible on the Linux CI runner this evidence check runs against."

### Changed
```
 tickets/T-3781/ticket.md | 31 ++++++++++++++++++++++++++++++-
 1 file changed, 30 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestParsedArtifacts::test_store_then_load_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestParsedArtifacts::test_load_miss_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestParsedArtifacts::test_different_fingerprint_is_a_separate_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestParsedArtifacts::test_store_overwrites_existing_payload` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sibling_reader_survives_concurrent_recreate` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_quarantined_sidecars_are_renamed_not_unlinked` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sweep_removes_only_old_quarantined_sidecars` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_recreate_replacement_always_has_meta_table` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_first_ever_connect_never_exposes_a_tableless_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_run_with_stale_reconnect_recovers_from_bare_database_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_check_fingerprint_with_recovery_recovers_from_bare_database_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_run_with_stale_reconnect_recovers_from_interface_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_check_fingerprint_with_recovery_recovers_from_interface_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_is_stale_or_corrupt_connection_matches_interface_error_by_type` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_apply_schema_rebuild_replacement_always_has_files_table` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_connect_after_forced_schema_rebuild_returns_a_fresh_live_connection` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_recreate_closed_connection_raises_a_clean_programming_error_not_interface_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestLockBackoff::test_backoff_doubles_up_to_the_cap` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestLockBackoff::test_backoff_never_exceeds_remaining_budget` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestLockBackoff::test_backoff_is_never_negative` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestHandleIdentity::test_identity_changes_after_os_replace` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestHandleIdentity::test_replaced_away_handle_is_reopened_before_the_next_read` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestHandleIdentity::test_live_handle_is_not_reopened` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestHandleIdentity::test_readonly_database_is_classified_as_a_handle_fault` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestHandleIdentity::test_lock_retry_lets_a_readonly_fault_escape_to_the_reopen_layer` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestHandleIdentity::test_fingerprint_read_after_a_replace_lands_on_the_live_file` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestHandleIdentity::test_store_file_data_after_a_replace_lands_on_the_live_file` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 28 passed (from 28 evidence id(s))
- gates: 0 error(s), 4346 warning(s), 922 waived
- error-findings: none (measured, zero errors)

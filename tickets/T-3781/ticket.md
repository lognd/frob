---
id: T-3781
title: fix win32 failures in graph cache sqlite handle tests
state: done
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_graph_cache.py
- src/frob/graph/cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/graph/**
  reason: narrow away from the whole graph package to avoid overlap with T-1608/T-1609/T-3213/T-3248/T-3573
  actor: logan
  at: '2026-09-04'
- op: add
  glob: src/frob/graph/cache.py
  reason: the sqlite cache module is the actual fix surface for the win32 handle/replace
    failures
  actor: logan
  at: '2026-09-04'
evidence:
- tests/unit/test_graph_cache.py::TestParsedArtifacts::test_store_then_load_round_trips
- tests/unit/test_graph_cache.py::TestParsedArtifacts::test_load_miss_returns_none
- tests/unit/test_graph_cache.py::TestParsedArtifacts::test_different_fingerprint_is_a_separate_key
- tests/unit/test_graph_cache.py::TestParsedArtifacts::test_store_overwrites_existing_payload
- tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sibling_reader_survives_concurrent_recreate
- tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_quarantined_sidecars_are_renamed_not_unlinked
- tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_sweep_removes_only_old_quarantined_sidecars
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_recreate_replacement_always_has_meta_table
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_first_ever_connect_never_exposes_a_tableless_file
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_run_with_stale_reconnect_recovers_from_bare_database_error
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_check_fingerprint_with_recovery_recovers_from_bare_database_error
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_run_with_stale_reconnect_recovers_from_interface_error
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_check_fingerprint_with_recovery_recovers_from_interface_error
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_is_stale_or_corrupt_connection_matches_interface_error_by_type
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_apply_schema_rebuild_replacement_always_has_files_table
- tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_connect_after_forced_schema_rebuild_returns_a_fresh_live_connection
- tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_recreate_closed_connection_raises_a_clean_programming_error_not_interface_error
- tests/unit/test_graph_cache.py::TestLockBackoff::test_backoff_doubles_up_to_the_cap
- tests/unit/test_graph_cache.py::TestLockBackoff::test_backoff_never_exceeds_remaining_budget
- tests/unit/test_graph_cache.py::TestLockBackoff::test_backoff_is_never_negative
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_identity_changes_after_os_replace
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_replaced_away_handle_is_reopened_before_the_next_read
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_live_handle_is_not_reopened
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_readonly_database_is_classified_as_a_handle_fault
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_lock_retry_lets_a_readonly_fault_escape_to_the_reopen_layer
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_fingerprint_read_after_a_replace_lands_on_the_live_file
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_store_file_data_after_a_replace_lands_on_the_live_file
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI failures in tests/unit/test_graph_cache.py (6): TestConnectNeverReturnsAStaleConnection, TestHandleIdentity (3), TestRecreateConcurrentReaderSurvives, TestRecreateNeverExposesASchemaIncompleteDb. Likely sqlite file-handle/replace on Windows (Windows forbids replacing/removing an open file) needing a real fix (close handle before os.replace, or retry-on-PermissionError).
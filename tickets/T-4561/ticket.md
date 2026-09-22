---
id: T-4561
title: 'post-land sweep residue from T-4517: COV002 in src/frob/lang/_support.py and
  src/frob/testing/_collect_csharp.py (new public symbols lack frob:doc/frob:tests
  edges)'
state: done
kind: bug
origin: agent
created: '2026-09-17'
priority: medium
parent: T-4513
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: v0.533.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_support.py
- src/frob/testing/_collect_csharp.py
- docs/modules/testing.md
- tests/unit/test_collect_csharp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
evidence:
- tests/unit/test_collect_csharp.py::TestCapabilityTestDiscoveryStatusCsharp::test_csharp_test_discovery_is_implemented
- tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_content_key_changes_when_file_content_changes
- tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_load_cache_key_mismatch_is_a_miss
- tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_load_cache_missing_file_is_a_miss
- tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_load_cache_unreadable_json_is_a_miss
- tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_store_cache_writes_sorted_node_ids
- tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_store_then_load_round_trips
- tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods::test_attribute_names_reads_bare_names_off_a_method_node
- tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods::test_parameterized_test_case_collapses_to_one_qualname
- tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods::test_setup_method_is_excluded
- tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods::test_test_attributed_method_is_found_with_its_qualname
- tests/unit/test_collect_csharp.py::TestCsNodeIdAndCollectCsFile::test_collect_cs_file_returns_node_ids
- tests/unit/test_collect_csharp.py::TestCsNodeIdAndCollectCsFile::test_node_id_shape
- tests/unit/test_collect_csharp.py::TestCsNodeIdAndCollectCsFile::test_unreadable_file_returns_empty_list_not_a_raise
- tests/unit/test_collect_csharp.py::TestFindCsFiles::test_finds_nested_cs_files_only
- tests/unit/test_collect_csharp.py::TestFindCsFiles::test_no_cs_files_is_empty_list
- tests/unit/test_collect_csharp.py::TestMatchDirExcluded::test_descendant_match
- tests/unit/test_collect_csharp.py::TestMatchDirExcluded::test_exact_dir_match
- tests/unit/test_collect_csharp.py::TestMatchDirExcluded::test_unrelated_dir_is_not_excluded
designated_repro_test: null
acceptance:
- text: GIVEN the T-4517 symbols in _support.py and _collect_csharp.py WHEN frob check
    runs THEN COV002 reports 0 findings for both files
  evidence:
  - tests/unit/test_collect_csharp.py::TestCapabilityTestDiscoveryStatusCsharp::test_csharp_test_discovery_is_implemented
  - tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_content_key_changes_when_file_content_changes
  - tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_load_cache_key_mismatch_is_a_miss
  - tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_load_cache_missing_file_is_a_miss
  - tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_load_cache_unreadable_json_is_a_miss
  - tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_store_cache_writes_sorted_node_ids
  - tests/unit/test_collect_csharp.py::TestContentKeyAndCache::test_store_then_load_round_trips
  - tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods::test_attribute_names_reads_bare_names_off_a_method_node
  - tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods::test_parameterized_test_case_collapses_to_one_qualname
  - tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods::test_setup_method_is_excluded
  - tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods::test_test_attributed_method_is_found_with_its_qualname
  - tests/unit/test_collect_csharp.py::TestCsNodeIdAndCollectCsFile::test_collect_cs_file_returns_node_ids
  - tests/unit/test_collect_csharp.py::TestCsNodeIdAndCollectCsFile::test_node_id_shape
  - tests/unit/test_collect_csharp.py::TestCsNodeIdAndCollectCsFile::test_unreadable_file_returns_empty_list_not_a_raise
  - tests/unit/test_collect_csharp.py::TestFindCsFiles::test_finds_nested_cs_files_only
  - tests/unit/test_collect_csharp.py::TestFindCsFiles::test_no_cs_files_is_empty_list
  - tests/unit/test_collect_csharp.py::TestMatchDirExcluded::test_descendant_match
  - tests/unit/test_collect_csharp.py::TestMatchDirExcluded::test_exact_dir_match
  - tests/unit/test_collect_csharp.py::TestMatchDirExcluded::test_unrelated_dir_is_not_excluded
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4561
branch: t-4561
---
Raised by the post-land sweep of bcd55a738 (T-4517). Quarantine findings COV002:src/frob/lang/_support.py and COV002:src/frob/testing/_collect_csharp.py are filed onto this ticket. frob:waive BUG002 reason="sweep residue: the defect is a missing coverage edge, not runtime behaviour; no repro test can fail at parent"
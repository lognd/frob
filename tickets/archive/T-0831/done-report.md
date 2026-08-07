## Done report

Refs gate token-reach now answers via a precomputed reverse index
(exact-token, slash-suffix, dot-suffix maps built once) instead of the
O(files^2 x tokens) pairwise rescan; violations proven byte-identical
against the pre-change code on the same checkout (90 both, zero diff)
and the isolated ref_gate call drops 10.1s -> ~1.3s wall.

### Changed
```
 src/frob/gates/_refs.py |  98 ++++++++++++++++++++++++++++++++++---------
 tickets.md              | 108 +++++++++++++++++++++++++++++++++++++++++++++++-
 2 files changed, 184 insertions(+), 22 deletions(-)
```

### Evidence
- `tests/test_refs_gate.py::TestTiers::test_zero_refs_warns_ref001` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestTiers::test_one_ref_weak_warns_ref002` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestTiers::test_two_refs_passes` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestUsedByDeclaration::test_valid_declaration_counts_not_dangling` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_nonexistent_consumer_fails` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_non_reaching_consumer_fails` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestEntrypointAllowlist::test_allowlisted_file_is_exempt` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestEntrypointAllowlist::test_non_allowlisted_orphan_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestNativeStubLinking::test_linked_pyi_beside_matching_manifest_does_not_fire_ref001` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestNativeStubLinking::test_unlinked_pyi_with_no_adjacent_module_still_fires_ref001` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestNativeStubLinking::test_pyi_with_manifest_present_but_module_name_mismatch_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestSeverityAndDegrade::test_no_tracked_files_returns_empty` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReferenceDetection::test_bare_prose_mention_does_not_count_as_a_reference` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReferenceDetection::test_markdown_link_counts_as_a_reference` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_multi_name_from_import_target_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_parenthesized_from_import_target_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dispatch_table_bare_string_target_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_pytest_collected_test_file_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dead_non_test_file_under_tests_dir_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_registry_style_yaml_with_only_prose_mentions_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestReviewerRegressionRound2::test_genuinely_unreferenced_module_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_suppressed_by_inline_waive` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_without_waive_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_path_mention_counts_as_reference` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_bare_identifier_not_treated_as_reference` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 26 passed (from 26 evidence id(s))
- gates: -1 error(s), -1 warning(s), -1 waived

---
id: T-0831
title: 'refs gate: O(files^2) pairwise token-reach scan in _auto_inbound/_tokens_reach
  dominates refs stage (13.5s CPU)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_refs.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_refs_gate.py::TestTiers::test_zero_refs_warns_ref001
- tests/test_refs_gate.py::TestTiers::test_one_ref_weak_warns_ref002
- tests/test_refs_gate.py::TestTiers::test_two_refs_passes
- tests/test_refs_gate.py::TestUsedByDeclaration::test_valid_declaration_counts_not_dangling
- tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_nonexistent_consumer_fails
- tests/test_refs_gate.py::TestUsedByDeclaration::test_dangling_declaration_non_reaching_consumer_fails
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_allowlisted_file_is_exempt
- tests/test_refs_gate.py::TestEntrypointAllowlist::test_non_allowlisted_orphan_still_fires
- tests/test_refs_gate.py::TestNativeStubLinking::test_linked_pyi_beside_matching_manifest_does_not_fire_ref001
- tests/test_refs_gate.py::TestNativeStubLinking::test_unlinked_pyi_with_no_adjacent_module_still_fires_ref001
- tests/test_refs_gate.py::TestNativeStubLinking::test_pyi_with_manifest_present_but_module_name_mismatch_still_fires
- tests/test_refs_gate.py::TestSeverityAndDegrade::test_all_violations_are_warn_severity
- tests/test_refs_gate.py::TestSeverityAndDegrade::test_no_tracked_files_returns_empty
- tests/test_refs_gate.py::TestReferenceDetection::test_bare_prose_mention_does_not_count_as_a_reference
- tests/test_refs_gate.py::TestReferenceDetection::test_markdown_link_counts_as_a_reference
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_multi_name_from_import_target_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_parenthesized_from_import_target_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dispatch_table_bare_string_target_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_pytest_collected_test_file_not_flagged
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_dead_non_test_file_under_tests_dir_still_fires
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_registry_style_yaml_with_only_prose_mentions_still_fires
- tests/test_refs_gate.py::TestReviewerRegressionRound2::test_genuinely_unreferenced_module_still_fires
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_suppressed_by_inline_waive
- tests/test_refs_gate.py::TestMarkdownWaive::test_ref002_on_md_doc_without_waive_still_fires
- tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_path_mention_counts_as_reference
- tests/test_refs_gate.py::TestBacktickTokenizer::test_backtick_wrapped_bare_identifier_not_treated_as_reference
designated_repro_test: null
threat: null
component: null
---
T-0582 (perf audit re-measurement) profiled the refs gate in isolation
(cProfile over a direct ref_gate(root) call, natives built, warm parse
cache). It IS the confirmed 2nd-largest gate-summary dominator (refs=13.52s
CPU in a real `frob check` run on this checkout, second only to test=16.72s;
everything else is under 8s).

Root cause, not re-parsing: `_auto_inbound` (src/frob/gates/_refs.py:502)
calls `_tokens_reach` (src/frob/gates/_refs.py:465) for every (candidate,
other) pair of the 994 tracked files -- an O(files^2) nested scan. Inside
`_tokens_reach`, two of the fallback checks are themselves O(tokens-in-file)
generator scans (`any(token.endswith(...) for token in tokens)`), so the
real cost is O(files^2 * tokens_per_file). Isolated cProfile measured 38.6M
calls into the `token.endswith("/" + basename)` genexpr at line 492 alone
(71.4s tottime under cProfile instrumentation), plus 19.5M more at the
stem-suffix genexpr at line 502 (23.7s tottime) -- both dwarfing everything
else in the gate (`endswith` itself: 95.9M calls, 56.9s tottime). isolated
wall under cProfile was 226.59s (profiler-inflated; the trustworthy number
is the real run's thread_time refs=13.52s CPU, consistent with an O(n^2)
shape at n~994 without cProfile's per-call overhead multiplier).

Fix direction: replace the O(files^2) pairwise scan with a reverse index
built once, O(files * tokens_per_file): for every tracked file, extract its
own basename/full-path/stem as index keys and its `_candidate_tokens` set;
build a dict from (basename suffix / stem suffix) -> the set of files whose
own path could satisfy that suffix, then for each candidate look up its own
basename/stem against a SINGLE combined trie/suffix index of all tokens
across all files, rather than re-scanning every other file's raw token set
per candidate. A simpler bounded win: precompute, once, a flat
multiset/Counter of every token's trailing path-segment and stem across all
files (a single O(total_tokens) pass), then `_tokens_reach` becomes an O(1)
dict lookup instead of an O(tokens_in_one_file) scan repeated per candidate
pair. Either shape turns the current O(files^2 * tokens_per_file) into
roughly O(files * tokens_per_file), which is the actual win refs needs.

Not fixed as part of T-0582: `src/frob/gates/_refs.py` is outside T-0582's
declared scope (src/frob/vet/, docs/audits/perf.md). This ticket is the
paired fix for the "profile refs stage" half of T-0582's re-measurement
mandate. See docs/audits/perf.md's dated re-measurement section for the
full T-0582 measurement table.
---
id: T-1086
title: 'arch: split remaining T-1076 tier-2 large files (dup/_pipeline, ticket_runner,
  tickets/__init__, _land)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/dup/_pipeline.py
- src/frob/app/ticket_runner.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_dup.py::TestR3LiteralAbstraction::test_r3_fires_where_r2_does_not
- tests/test_dup.py::TestErrorChannelDupPairing::test_result_and_optional_git_common_dir_register_as_a_duplicate_group
- tests/test_dup.py::TestConditionalShapeDupPairing::test_combined_vs_split_guard_git_common_dir_registers_as_a_duplicate_group
- tests/test_dup_smart.py::TestTouchedRefs::test_hunk_overlapping_span_marks_symbol_touched
- tests/test_dup_region.py::TestRegionKernelOffByDefault::test_disabled_by_default_finds_no_region_pairs
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_python_block_still_matches
- tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_both_languages_parse_into_the_snapshot
- tests/test_dup_native_rungs.py::TestNativeRungsDefaultsOnForDirectCallers::test_default_config_still_reports_native_rungs
- tests/test_dup_inline.py::TestHelperInliningLitmus::test_split_helpers_detected_with_inlining
- tests/test_dup_rungs.py::TestR4NearMiss::test_fires_on_gapped_clone
- tests/test_dup_prefilter.py::TestCharacteristicVector::test_identical_streams_have_identical_vectors
- tests/unit/test_dup_smt.py::test_degrades_to_smt_unavailable_without_z3
designated_repro_test: null
threat: null
component: null
---
T-1076 remainder: after this pass split src/frob/__main__.py (2615 lines) into
a src/frob/_cli_parsers/ package (5 files, all under 950 lines, __init__.py
re-exporting the full original surface -- T-1072/T-0989 pattern, same as the
earlier _pii_structural split), four files from T-1076's original tier-2
large-file list are still untouched and still over the 2000-5000 line
large-file gate threshold:

- src/frob/dup/_pipeline.py (2628 lines) -- note the _PII012_REVIEWED_NON_PII
  allowlist entries now live under src/frob/gates/_pii_structural/ (moved
  there by the earlier _pii_structural split in this same T-1076 pass); any
  split here that moves a (file, token) entry referenced by that allowlist
  must carry the allowlist edit with it.
- src/frob/app/ticket_runner.py (3957 lines)
- src/frob/tickets/__init__.py (4260 lines)
- src/frob/tickets/_land.py (4762 lines)

Each needs its own module-split plan (cohesive sibling files, re-exported
surface unchanged, zero caller edits, every frob:ticket/frob:tests/frob:doc
directive carried WITH its symbol) and full-suite verification per file,
landed incrementally -- do not batch all four into one diff.
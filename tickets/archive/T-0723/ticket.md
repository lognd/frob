---
id: T-0723
title: 'lang: wire kotlin into central dispatch (_EXTENSION_TABLE + RawSymbol walker
  + COMMENT_TYPES)'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0614
parent: T-0329
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/unit/test_lang_kotlin.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kt_fixture_parses_without_error
- tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kts_fixture_parses_without_error
- tests/unit/test_lang_kotlin.py::TestParseKotlin::test_top_level_node_types_include_class_and_fun
- tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_returns_tree_node
- tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_comments_are_stripped
- tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_comment_types_cover_kotlin_line_and_block_comments
- tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_walks_top_level_function
- tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_walks_class_and_method
- tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_interface_method_has_no_body
- tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_private_symbol_is_not_public
- tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_top_level_property_and_typealias
- tests/unit/test_lang_kotlin.py::TestWalkKotlin::test_leading_kdoc_comment_binds_as_doc_text
- tests/unit/test_lang_kotlin.py::TestParseFileDispatchesKotlin::test_kt_file_parses_into_the_symbol_graph
- tests/unit/test_lang_kotlin.py::TestParseFileDispatchesKotlin::test_kts_extension_also_dispatches
- tests/unit/test_lang_kotlin.py::TestParseFileDispatchesKotlin::test_kotlin_is_a_supported_language_and_extension
designated_repro_test: null
acceptance:
- text: GIVEN a repo with a .kt file WHEN frob check runs THEN the file parses into
    the symbol graph (no KeyError) and its symbols appear in frob map output
  evidence:
  - tests/unit/test_lang_kotlin.py::TestParseFileDispatchesKotlin::test_kt_file_parses_into_the_symbol_graph
  - tests/unit/test_lang_kotlin.py::TestParseFileDispatchesKotlin::test_kts_extension_also_dispatches
threat: null
component: null
---
T-0614's KotlinAdapter works standalone but .kt/.kts files are invisible to parse_file/frob check: _EXTENSION_TABLE lacks the extensions and _extract.py's _WALKERS dict-subscript (line ~91, no fallback) would KeyError if the table alone were wired. Deliver the RawSymbol walker for kotlin (mirroring the TS/Rust walkers in _extract.py), COMMENT_TYPES entry, and the extension-table wiring together, with tests proving a real .kt file flows through parse_file into the graph. Was T-0723 (ex-draft, id lost at land) (prose-only) in T-0614's Done report.
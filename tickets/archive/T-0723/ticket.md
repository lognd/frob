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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/**
- tests/unit/test_lang_kotlin.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_kotlin.py'
  actor: logan
  at: '2026-09-19'
  old_length: 551
  new_length: 2277
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
anchor: false
anchor_reason: null
land_commit: null
---
T-0614's KotlinAdapter works standalone but .kt/.kts files are invisible to parse_file/frob check: _EXTENSION_TABLE lacks the extensions and _extract.py's _WALKERS dict-subscript (line ~91, no fallback) would KeyError if the table alone were wired. Deliver the RawSymbol walker for kotlin (mirroring the TS/Rust walkers in _extract.py), COMMENT_TYPES entry, and the extension-table wiring together, with tests proving a real .kt file flows through parse_file into the graph. Was T-0723 (ex-draft, id lost at land) (prose-only) in T-0614's Done report.

T-4718 sweep (condensed from src/frob/vet/_capability_kotlin.py:19-42,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# --------------------------------------------------------------- kotlin (T-0664)
#
# Kotlin static-binding resolution (docs/design/capability-evasion-
# taxonomy.md's Kotlin table, T-0664 -- the fourth per-language resolver
# after T-0328/T-0377/T-0378/T-0379/T-0662/T-0663's python/TS/rust/C/C++
# ones). `frob.lang.raw_tree`'s `"kotlin"` label reaches `frob.lang._walk_
# kotlin`'s grammar via T-0723's central-dispatch wiring.
#
# SCOPE, disclosed up front rather than silently narrowed: this resolver
# uses a FLAT, FILE-WIDE alias table (no per-scope/position shadow
# discipline the way `_c_shadowing_scope`/`_rust_shadowing_scope` give the
# C/rust resolvers) -- a local variable that happens to share a name with
# an imported/aliased binding is NOT distinguished from the import here.
# This is a REDUCED-FIDELITY model versus the other four resolvers (a
# genuine over-approximation risk, not a silent gap: a shadowing local
# could theoretically cause a spurious "detected" on a name that is
# locally rebound to something harmless), accepted for this pass given
# kotlin's own grammar has no separate compilation-unit-vs-function-body
# scope split as clean as C's `_C_SCOPE_TYPES`/rust's `_RUST_SCOPE_TYPES`
# to hang position-aware bookkeeping off of without materially more
# machinery than this ticket's own time budget allows. A future pass
# tightening this to per-function scoping (mirroring `_c_scope_bound_
# names`'s shape against kotlin's `function_declaration`/`class_body`
# nodes) is a natural follow-up, not attempted here.
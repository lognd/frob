---
id: T-0613
title: 'arch: wire tree-sitter-kotlin grammar into frob.lang'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0329
tier: ticket
sprint: null
scope:
- pyproject.toml
- src/frob/lang/_walk_kotlin.py
- tests/unit/test_lang_kotlin.py
- CHANGELOG.md
- uv.lock
- .frob-release.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_lang_kotlin.py
  reason: smoke test proving the T-0613 raw kotlin walk parses .kt/.kts fixtures without
    error, required by the ticket's own acceptance criteria
  actor: logan
  at: '2026-07-22'
- op: add
  glob: CHANGELOG.md
  reason: REL001 requires a version bump + CHANGELOG entry for the new public API
    this ticket adds (parse_kotlin/raw_kotlin_tree/COMMENT_TYPES)
  actor: logan
  at: '2026-07-22'
- op: add
  glob: uv.lock
  reason: uv sync regenerates uv.lock's pinned frob version when pyproject.toml's
    [project].version bumps for REL001
  actor: logan
  at: '2026-07-22'
- op: add
  glob: .frob-release.json
  reason: frob release stamp updates this manifest as part of satisfying REL001 for
    the version bump this ticket's new public API required
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kt_fixture_parses_without_error
- tests/unit/test_lang_kotlin.py::TestParseKotlin::test_kts_fixture_parses_without_error
- tests/unit/test_lang_kotlin.py::TestParseKotlin::test_top_level_node_types_include_class_and_fun
- tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_returns_tree_node
- tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_comments_are_stripped
- tests/unit/test_lang_kotlin.py::TestRawKotlinTree::test_comment_types_cover_kotlin_line_and_block_comments
designated_repro_test: null
threat: null
component: null
---
Add tree-sitter-kotlin as a dependency (or via tree-sitter-language-pack if it covers kotlin; otherwise pin tree-sitter-kotlin directly) and add a minimal _walk_kotlin.py following the _walk_typescript.py/_walk_rust.py shape (parse, expose raw tree-sitter nodes) with no normalized-model mapping yet. Acceptance: a trivial .kt fixture parses without error; a smoke test asserts the parse tree has expected top-level node types (class, fun).
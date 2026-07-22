"""Kotlin raw tree-sitter wiring (T-0613, epic T-0329 child).

Scope is deliberately narrow: parse `.kt`/`.kts` source via
`tree-sitter-language-pack`'s bundled kotlin grammar and expose the raw
tree-sitter nodes, with NO normalized-model mapping yet -- that adapter
(mapping kotlin's node vocabulary onto the T-0609 normalized code model
the same way `_walk_typescript.py`/`_walk_rust.py` map theirs) is T-0614's
job, blocked on this ticket plus T-0610. Central dispatch wiring
(`frob.lang.__init__`'s `_EXTENSION_TABLE`, `_extract.py`'s `_WALKERS`/
`COMMENT_TYPES`) is likewise left to T-0614 -- this module is usable
standalone today (see `parse_kotlin`/`raw_kotlin_tree`) but not yet reached
through `frob.lang.parse_file`.
"""

from __future__ import annotations

from tree_sitter import Tree
from tree_sitter_language_pack import get_parser

from frob.lang._common import export_tree
from frob.lang._models import TreeNode

# tree-sitter-kotlin's grammar name inside tree-sitter-language-pack.
_GRAMMAR_NAME = "kotlin"

# frob:ticket T-0613
# frob:doc docs/modules/lang.md#per-language-walker-notes
# frob:tests tests/unit/test_lang_kotlin.py::TestRawKotlinTree.test_comment_types_cover_kotlin_line_and_block_comments  # noqa: E501
# Kotlin's two comment node types (docs/modules/lang.md extraction table
# convention, mirroring `_extract.py`'s per-language `COMMENT_TYPES`):
# `// ...` and `/* ... */` respectively.
COMMENT_TYPES = frozenset({"line_comment", "multiline_comment"})


# frob:ticket T-0613
# frob:doc docs/modules/lang.md#per-language-walker-notes
# frob:tests tests/unit/test_lang_kotlin.py::TestParseKotlin.test_kt_fixture_parses_without_error  # noqa: E501
# frob:tests tests/unit/test_lang_kotlin.py::TestParseKotlin.test_kts_fixture_parses_without_error  # noqa: E501
# frob:tests tests/unit/test_lang_kotlin.py::TestParseKotlin.test_top_level_node_types_include_class_and_fun  # noqa: E501
def parse_kotlin(source: bytes) -> Tree:
    """Parse kotlin source bytes into a tree-sitter `Tree` via the language
    pack's bundled kotlin grammar (no separate `tree-sitter-kotlin` pin
    needed -- see pyproject.toml's T-0613 comment)."""
    parser = get_parser(_GRAMMAR_NAME)
    return parser.parse(source)


# frob:ticket T-0613
# frob:doc docs/modules/lang.md#per-language-walker-notes
# frob:tests tests/unit/test_lang_kotlin.py::TestRawKotlinTree.test_returns_tree_node
# frob:tests tests/unit/test_lang_kotlin.py::TestRawKotlinTree.test_comments_are_stripped  # noqa: E501
def raw_kotlin_tree(source: bytes) -> TreeNode:
    """Raw `TreeNode` export of `source`'s full kotlin parse tree, comments
    stripped -- the raw-walk-only surface this ticket adds; no
    normalized-model mapping (that is T-0614's adapter, not this
    function's job)."""
    tree = parse_kotlin(source)
    return export_tree(tree.root_node, COMMENT_TYPES)

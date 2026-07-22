"""Smoke tests for the T-0613 raw kotlin tree-sitter wiring.

Proves `frob.lang._walk_kotlin` parses trivial `.kt`/`.kts` source without
error and that the resulting tree has the expected top-level node types
(class, fun) -- the ticket's stated acceptance criteria. No normalized-
model assertions here: that mapping is T-0614's job, not this module's.
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._models import TreeNode
from frob.lang._walk_kotlin import COMMENT_TYPES, parse_kotlin, raw_kotlin_tree

_KT_SOURCE = b"""\
// a leading comment
package com.example.frob

class Greeter(val name: String) {
    fun greet(): String {
        return "hello, " + name
    }
}
"""

_KTS_SOURCE = b"""\
fun main() {
    println("hello from a script")
}
"""


class TestParseKotlin:
    """`parse_kotlin` produces a usable tree-sitter tree for `.kt`/`.kts` source."""

    def test_kt_fixture_parses_without_error(self) -> None:
        """A trivial `.kt` fixture parses with no `ERROR`/`MISSING` nodes."""
        tree = parse_kotlin(_KT_SOURCE)
        assert not tree.root_node.has_error
        assert tree.root_node.type == "source_file"

    def test_kts_fixture_parses_without_error(self) -> None:
        """A trivial `.kts` script fixture parses with no `ERROR`/`MISSING` nodes."""
        tree = parse_kotlin(_KTS_SOURCE)
        assert not tree.root_node.has_error
        assert tree.root_node.type == "source_file"

    def test_top_level_node_types_include_class_and_fun(self) -> None:
        """The `.kt` fixture's parse tree has a top-level class and a
        nested function declaration -- the acceptance criteria's "class,
        fun" node-type check."""
        tree = parse_kotlin(_KT_SOURCE)
        top_level_types = {child.type for child in tree.root_node.children}
        assert "class_declaration" in top_level_types

        def collect_types(node: Node) -> set[str]:
            types = {node.type}
            for child in node.children:
                types |= collect_types(child)
            return types

        all_types = collect_types(tree.root_node)
        assert "function_declaration" in all_types


class TestRawKotlinTree:
    """`raw_kotlin_tree` exposes the parse as a `TreeNode`, comments stripped."""

    def test_returns_tree_node(self) -> None:
        """The export is a `TreeNode`, matching every other language's raw-walk shape."""
        node = raw_kotlin_tree(_KT_SOURCE)
        assert isinstance(node, TreeNode)
        assert node.label == "source_file"

    def test_comments_are_stripped(self) -> None:
        """A leading `// ...` comment never appears as an exported child node."""
        node = raw_kotlin_tree(_KT_SOURCE)

        def labels(n: TreeNode) -> set[str]:
            found = {n.label}
            for child in n.children:
                found |= labels(child)
            return found

        assert "line_comment" not in labels(node)

    def test_comment_types_cover_kotlin_line_and_block_comments(self) -> None:
        """`COMMENT_TYPES` names both of kotlin's comment node types."""
        assert COMMENT_TYPES == frozenset({"line_comment", "multiline_comment"})

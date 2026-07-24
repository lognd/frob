"""Smoke tests for the T-0613 raw kotlin tree-sitter wiring.

Proves `frob.lang._walk_kotlin` parses trivial `.kt`/`.kts` source without
error and that the resulting tree has the expected top-level node types
(class, fun) -- the ticket's stated acceptance criteria. No normalized-
model assertions here: that mapping is T-0614's job, not this module's.
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Node

import frob.lang as lang_pkg
from frob.lang._models import RawSymbol, SymbolKind, TreeNode
from frob.lang._walk_kotlin import (
    COMMENT_TYPES,
    _walk_kotlin,
    parse_kotlin,
    raw_kotlin_tree,
)

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


_WALK_SOURCE = b"""\
/** doc for greeter */
class Greeter(val name: String) {
    /** greet doc */
    fun greet(): String {
        return "hello, " + name
    }

    private fun helper() {}
}

interface Iface {
    fun greet(): String
}

typealias Str = String

val topLevel: Int = 5

fun main() {
    println("hi")
}
"""


class TestWalkKotlin:
    """`_walk_kotlin` (T-0723) -- the `RawSymbol` walker `frob.lang._extract`'s
    `_WALKERS` dispatch table needs so a real `.kt` file flows into the
    symbol graph without a `KeyError`."""

    def test_walks_top_level_function(self) -> None:
        """A top-level `fun main()` becomes a public `FUNCTION` symbol."""
        tree = parse_kotlin(_WALK_SOURCE)
        symbols = _walk_kotlin(tree.root_node)
        main = next(s for s in symbols if s.qualname == "main")
        assert main.kind == SymbolKind.FUNCTION
        assert main.public is True

    def test_walks_class_and_method(self) -> None:
        """A class and its method both appear, the method dotted under the class."""
        tree = parse_kotlin(_WALK_SOURCE)
        symbols = _walk_kotlin(tree.root_node)
        by_qualname = {s.qualname: s for s in symbols}
        assert by_qualname["Greeter"].kind == SymbolKind.CLASS
        assert by_qualname["Greeter.greet"].kind == SymbolKind.METHOD
        assert "hello" in " ".join(by_qualname["Greeter.greet"].body_tokens)

    def test_interface_method_has_no_body(self) -> None:
        """A bodyless interface method still binds (kotlin folds `interface`
        into the same `class_declaration` node type as `class`)."""
        tree = parse_kotlin(_WALK_SOURCE)
        symbols = _walk_kotlin(tree.root_node)
        by_qualname = {s.qualname: s for s in symbols}
        assert by_qualname["Iface"].kind == SymbolKind.CLASS
        assert by_qualname["Iface.greet"].body_tokens == ()

    def test_private_symbol_is_not_public(self) -> None:
        """An explicit `private` modifier marks the symbol non-public."""
        tree = parse_kotlin(_WALK_SOURCE)
        symbols = _walk_kotlin(tree.root_node)
        by_qualname = {s.qualname: s for s in symbols}
        assert by_qualname["Greeter.helper"].public is False

    def test_top_level_property_and_typealias(self) -> None:
        """A top-level `val` becomes a `CONST`, a `typealias` becomes a `TYPE`."""
        tree = parse_kotlin(_WALK_SOURCE)
        symbols = _walk_kotlin(tree.root_node)
        by_qualname = {s.qualname: s for s in symbols}
        assert by_qualname["topLevel"].kind == SymbolKind.CONST
        assert by_qualname["Str"].kind == SymbolKind.TYPE

    def test_leading_kdoc_comment_binds_as_doc_text(self) -> None:
        """A `/** ... */` KDoc block directly above a class/fn binds as `doc_text`."""
        tree = parse_kotlin(_WALK_SOURCE)
        symbols = _walk_kotlin(tree.root_node)
        by_qualname = {s.qualname: s for s in symbols}
        assert "doc for greeter" in by_qualname["Greeter"].doc_text
        assert "greet doc" in by_qualname["Greeter.greet"].doc_text


class TestParseFileDispatchesKotlin:
    """`frob.lang.parse_file` (central dispatch) reaches `.kt`/`.kts` files --
    T-0723's own acceptance criterion: no `KeyError`, real symbols back."""

    def test_kt_file_parses_into_the_symbol_graph(self, tmp_path: Path) -> None:
        """A real `.kt` file on disk flows through `parse_file` into `RawSymbol`s."""
        kt_file = tmp_path / "Greeter.kt"
        kt_file.write_bytes(_WALK_SOURCE)
        result = lang_pkg.parse_file(kt_file)
        assert result.is_ok
        parsed = result.danger_ok
        assert parsed.language == "kotlin"
        qualnames = {s.qualname for s in parsed.symbols}
        assert "Greeter" in qualnames
        assert "Greeter.greet" in qualnames
        assert isinstance(parsed.symbols[0], RawSymbol)

    def test_kts_extension_also_dispatches(self, tmp_path: Path) -> None:
        """`.kts` script files resolve to the same "kotlin" language label."""
        kts_file = tmp_path / "script.kts"
        kts_file.write_bytes(b'fun main() {\n    println("hi")\n}\n')
        result = lang_pkg.parse_file(kts_file)
        assert result.is_ok
        assert result.danger_ok.language == "kotlin"

    def test_kotlin_is_a_supported_language_and_extension(self) -> None:
        """`supported_languages`/`supported_extensions` both learn about kotlin."""
        assert "kotlin" in lang_pkg.supported_languages()
        assert ".kt" in lang_pkg.supported_extensions()
        assert ".kts" in lang_pkg.supported_extensions()

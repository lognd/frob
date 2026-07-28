"""Kotlin raw tree-sitter wiring (T-0613, epic T-0329 child).

Scope is deliberately narrow: parse `.kt`/`.kts` source via
`tree-sitter-language-pack`'s bundled kotlin grammar and expose the raw
tree-sitter nodes, with NO normalized-model mapping yet -- that adapter
(mapping kotlin's node vocabulary onto the T-0609 normalized code model
the same way `_walk_typescript.py`/`_walk_rust.py` map theirs) is T-0614's
job, blocked on this ticket plus T-0610. Central dispatch wiring
(`frob.lang.__init__`'s `_EXTENSION_TABLE`, `_extract.py`'s `_WALKERS`/
`COMMENT_TYPES`) is wired by T-0723's `_walk_kotlin` (below), mirroring
`_walk_rust.py`/`_walk_typescript.py`'s `RawSymbol` walker one node-kind at
a time -- see `_walk_kotlin` for the entry point `frob.lang._extract`
dispatches to.

GRAMMAR QUIRK (shared with `frob.arch._kotlin`, T-0614): unlike
`tree-sitter-typescript`/`tree-sitter-rust`, `tree-sitter-kotlin` (as
bundled by `tree-sitter-language-pack`) exposes almost no named fields --
`node.child_by_field_name(...)` returns `None` for essentially every node
type here. Every lookup below is therefore positional/type-based
(`_kt_child_of_type`: scan `node.children` for a specific `node.type`),
mirroring `frob.arch._kotlin._kt_child_of_type` exactly (kept as its own
copy here rather than a shared import -- `frob.lang` and `frob.arch` are
deliberately independent walk layers over the same grammar, matching how
`_walk_rust.py`/`frob.arch._rust.py` each keep their own node-walk code).
"""

from __future__ import annotations

from tree_sitter import Node, Tree
from tree_sitter_language_pack import get_parser

from frob.lang._common import (
    _canonical_tokens,
    _leading_doc_comment,
    _leaf_tokens,
    _span_of,
    child_text,
    export_tree,
)
from frob.lang._models import RawSymbol, SymbolKind, TreeNode

# tree-sitter-kotlin's grammar name inside tree-sitter-language-pack.
_GRAMMAR_NAME = "kotlin"

# frob:ticket T-0613
# frob:doc docs/modules/lang.md#per-language-walker-notes
# frob:tests tests/unit/test_lang_kotlin.py::TestRawKotlinTree.test_comment_types_cover_kotlin_line_and_block_comments  # noqa: E501
# Kotlin's two comment node types (docs/modules/lang.md extraction table
# convention, mirroring `_extract.py`'s per-language `COMMENT_TYPES`):
# `// ...` and `/* ... */`/`/** ... */` respectively.
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


# frob:waive DUP001 reason="see this function's own docstring -- deliberately \
# independent walk layer copy, same convention as frob.vet._capability/frob.arch \
# _kotlin's own copies (T-0861)"
def _kt_child_of_type(node: Node, type_name: str) -> Node | None:
    """The first DIRECT child of `node` with tree-sitter type `type_name`
    -- positional stand-in for a named-field lookup (see module docstring;
    mirrors `frob.arch._kotlin._kt_child_of_type`)."""
    for c in node.children:
        if c.type == type_name:
            return c
    return None


def _kt_has_visibility_modifier(node: Node, *names: str) -> bool:
    """True if `node`'s `modifiers` child carries a `visibility_modifier`
    whose own text is one of `names` (e.g. `"private"`, `"protected"`,
    `"internal"`)."""
    modifiers = _kt_child_of_type(node, "modifiers")
    if modifiers is None:
        return False
    return any(
        c.type == "visibility_modifier" and child_text(c) in names
        for c in modifiers.children
    )


def _kt_public(node: Node) -> bool:
    """Kotlin publicness: `public` by default -- only `private`/
    `protected`/`internal` narrow visibility (kotlin has no `pub`-style
    opt-in keyword, unlike rust's `_rust_public`)."""
    return not _kt_has_visibility_modifier(node, "private", "protected", "internal")


def _kt_function_symbol(
    node: Node, stack: tuple[str, ...], in_class: bool
) -> RawSymbol:
    """A `function_declaration` `RawSymbol` (method when inside a class/
    interface body, else a top-level function)."""
    name_node = _kt_child_of_type(node, "simple_identifier")
    name = child_text(name_node)
    body = _kt_child_of_type(node, "function_body")
    doc = _leading_doc_comment(node, COMMENT_TYPES)
    skip = ((body.start_byte, body.end_byte),) if body else ()
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD if in_class else SymbolKind.FUNCTION,
        public=_kt_public(node),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES, skip),
        body_tokens=_leaf_tokens(body, COMMENT_TYPES) if body else (),
        doc_text=doc,
        body_norm=_canonical_tokens(body, COMMENT_TYPES) if body else (),
    )


def _kt_class_symbol(node: Node, stack: tuple[str, ...]) -> RawSymbol:
    """A `class_declaration` `RawSymbol` (kotlin's grammar uses this same
    node type for both `class` and `interface` -- see module docstring)."""
    name_node = _kt_child_of_type(node, "type_identifier")
    name = child_text(name_node)
    doc = _leading_doc_comment(node, COMMENT_TYPES)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CLASS,
        public=_kt_public(node),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _kt_property_symbol(node: Node, stack: tuple[str, ...]) -> RawSymbol:
    """A top-level `property_declaration` (`val`/`var`) `RawSymbol` --
    kotlin's analogue of rust's `const_item`/`static_item`."""
    var_decl = _kt_child_of_type(node, "variable_declaration")
    name_node = _kt_child_of_type(var_decl, "simple_identifier") if var_decl else None
    name = child_text(name_node)
    doc = _leading_doc_comment(node, COMMENT_TYPES)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CONST,
        public=_kt_public(node),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _kt_typealias_symbol(node: Node, stack: tuple[str, ...]) -> RawSymbol:
    """A `type_alias` `RawSymbol` -- kotlin's analogue of rust's `type_item`."""
    name_node = _kt_child_of_type(node, "type_identifier")
    name = child_text(name_node)
    doc = _leading_doc_comment(node, COMMENT_TYPES)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.TYPE,
        public=_kt_public(node),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _kt_recurse_class(
    node: Node, stack: tuple[str, ...], symbols: list[RawSymbol]
) -> None:
    """Descend into a `class_declaration`'s `class_body` (its methods are members)."""
    name_node = _kt_child_of_type(node, "type_identifier")
    name = child_text(name_node)
    body = _kt_child_of_type(node, "class_body")
    if body is None:
        return
    # frob:invariant terminates reason="body is a direct positional child of node, and node is itself a child of the container passed to the caller's _kt_visit, so body is a proper descendant of that container in the finite tree-sitter parse tree" measure="container's subtree depth strictly decreases"  # noqa: E501
    _kt_visit(body, (*stack, name), symbols, in_class=True)


def _kt_visit(
    container: Node, stack: tuple[str, ...], symbols: list[RawSymbol], in_class: bool
) -> None:
    """Recursive descent appending kotlin symbols under `container`."""
    for node in container.children:
        if node.type == "function_declaration":
            symbols.append(_kt_function_symbol(node, stack, in_class))
        elif node.type == "class_declaration":
            symbols.append(_kt_class_symbol(node, stack))
            _kt_recurse_class(node, stack, symbols)
        elif node.type == "property_declaration" and not in_class:
            symbols.append(_kt_property_symbol(node, stack))
        elif node.type == "type_alias":
            symbols.append(_kt_typealias_symbol(node, stack))


# frob:ticket T-0723
# frob:tests tests/unit/test_lang_kotlin.py::TestWalkKotlin.test_walks_top_level_function  # noqa: E501
# frob:tests tests/unit/test_lang_kotlin.py::TestWalkKotlin.test_walks_class_and_method
# frob:tests tests/unit/test_lang_kotlin.py::TestWalkKotlin.test_interface_method_has_no_body  # noqa: E501
# frob:tests tests/unit/test_lang_kotlin.py::TestWalkKotlin.test_private_symbol_is_not_public  # noqa: E501
# frob:tests tests/unit/test_lang_kotlin.py::TestWalkKotlin.test_top_level_property_and_typealias  # noqa: E501
# frob:tests tests/unit/test_lang_kotlin.py::TestWalkKotlin.test_leading_kdoc_comment_binds_as_doc_text  # noqa: E501
def _walk_kotlin(root: Node) -> tuple[RawSymbol, ...]:
    """Every kotlin symbol: top-level/class functions (methods), classes
    (kotlin's grammar folds `interface` into the same `class_declaration`
    node type -- see module docstring), top-level `val`/`var` properties,
    and `typealias` declarations. The `RawSymbol` walker `frob.lang.
    _extract`'s `_WALKERS` dispatch table needs to turn a `.kt`/`.kts` file
    into symbols without a `KeyError` (T-0723's acceptance criterion)."""
    symbols: list[RawSymbol] = []
    _kt_visit(root, (), symbols, in_class=False)
    return tuple(symbols)

"""Rust symbol walker (docs/modules/lang.md extraction table).

Rust's `pub` visibility plus PyO3 export attributes (`#[pyfunction]`,
`#[pymethods]`, ...) define the crate's Python-facing public surface; that
publicness logic is kept here. The shared token/span/doc mechanism lives in
`_common.py`.
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    _leading_doc_comment,
    _leaf_tokens,
    _span_of,
    child_text,
)
from frob.lang._models import RawSymbol, SymbolKind

_COMMENT_TYPES = frozenset({"line_comment", "block_comment"})

# Test-generating macros: a `frob:tests` comment placed directly above one
# of these `<name>! { ... }` blocks (T-0318) needs a bindable symbol at the
# comment site even though the macro's expansion (one #[test] fn per case,
# synthesized at compile time) never exists as literal `function_item` AST
# nodes for `_visit` to see -- tree-sitter parses everything inside the
# macro's braces as an opaque `token_tree`, not structured items (verified
# directly: a `proptest! { #[test] fn foo(...) {...} }` block's body is one
# `token_tree` node, no `function_item` descendants at all). Extensible: add
# a macro name here to make it a recognized test-generator; anything not in
# this set is left alone (a `vec!`/`assert!`/etc. macro must never bind).
_TEST_MACRO_NAMES = frozenset({"proptest", "prop_compose"})

# The synthesized qualname suffix a test-macro symbol carries -- a literal
# `!` is never valid inside a real rust identifier, so `qualname.endswith`
# this marker unambiguously flags "this symbol is a macro-expansion stand-in,
# resolve its TESTS edges at file/module granularity" (gates/__init__.py's
# `_macro_symbol_file`) without needing a sixth `SymbolKind` bucket.
_MACRO_SYMBOL_SUFFIX = "!"

# PyO3 export attributes: an item carrying one of these is the crate's
# actual Python-facing public surface even without a `pub` keyword, so it
# must count as public for coverage/doc obligations. (`#[pymethods]` marks
# an impl block whose contained methods are all exported -- propagated by
# `_rust_public` via the enclosing container.)
_PYO3_EXPORT_ATTRS = ("pyfunction", "pymodule", "pyclass", "pymethods")


def _rust_has_pub(node: Node) -> bool:
    """True if `node` carries an explicit `pub` visibility modifier."""
    return any(c.type == "visibility_modifier" for c in node.children)


def _rust_pyo3_export(node: Node) -> bool:
    """True if a PyO3 export attribute precedes `node` (its own item)."""
    sib = node.prev_sibling
    while sib is not None and sib.type in (
        "attribute_item",
        "line_comment",
        "block_comment",
    ):
        if sib.type == "attribute_item" and any(
            marker in child_text(sib) for marker in _PYO3_EXPORT_ATTRS
        ):
            return True
        sib = sib.prev_sibling
    return False


def _rust_public(node: Node, in_pyo3_impl: bool = False) -> bool:
    """Rust publicness: an explicit `pub`, a direct PyO3 export attribute,
    or membership in a `#[pymethods]` impl (all its methods are exported)."""
    return in_pyo3_impl or _rust_has_pub(node) or _rust_pyo3_export(node)


def _symbol_span(node: Node) -> tuple[int, int]:
    """`_span_of(node)` widened backward over any directly preceding
    `#[...]` attribute stack (T-0278: a `// frob:doc`/`// frob:tests`
    comment placed above a stack of 2+ attribute lines, e.g.
    `#[derive(Debug)]` / `#[serde(...)]`, silently failed to bind).

    Rust's grammar keeps each `attribute_item` as its own SIBLING node
    directly before the item it decorates -- unlike python's
    `decorated_definition`, which wraps the whole decorator stack plus
    the def into one node whose span already starts at the first
    decorator (`_walk_python.py::_effective_node`). A rust item's own
    span therefore starts at the `pub fn`/`pub struct`/... keyword line,
    never at a preceding attribute. `_find_following_symbol` only looks
    within 2 lines past a comment (block)'s end line
    (`frob.lang._common`), so a directive sitting above a single
    attribute line still binds (1 line gap) but above 2+ stacked
    attribute lines does not (comment.py-still-correct math: `frob:doc`
    above two `#[...]` lines above the item puts the item's un-widened
    span 3+ lines below the comment). Widening the span used for
    comment-binding purposes ONLY (not `sig_tokens`, which still hashes
    `node` itself, unaffected) fixes this the same way `_effective_node`
    does for python, while leaving the below-all-attributes placement
    (the workaround already used in lithos/feldspar) still valid --
    it is unaffected since it was never broken."""
    start_node = node
    sib = node.prev_sibling
    while sib is not None and sib.type == "attribute_item":
        start_node = sib
        sib = sib.prev_sibling
    return (_span_of(start_node)[0], _span_of(node)[1])


def _function_symbol(
    node: Node, stack: tuple[str, ...], in_impl: bool, in_pyo3_impl: bool, doc: str
) -> RawSymbol:
    """A function/method `RawSymbol` (method when inside an impl/trait)."""
    name = child_text(node.child_by_field_name("name"))
    body = node.child_by_field_name("body")
    skip = ((body.start_byte, body.end_byte),) if body else ()
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD if in_impl else SymbolKind.FUNCTION,
        public=_rust_public(node, in_pyo3_impl),
        span=_symbol_span(node),
        sig_tokens=_leaf_tokens(node, _COMMENT_TYPES, skip),
        body_tokens=_leaf_tokens(body, _COMMENT_TYPES) if body else (),
        doc_text=doc,
    )


def _named_symbol(
    node: Node, stack: tuple[str, ...], kind: SymbolKind, doc: str
) -> RawSymbol:
    """A struct/trait/enum/type/const `RawSymbol` (no body tokens)."""
    name = child_text(node.child_by_field_name("name"))
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=kind,
        public=_rust_public(node),
        span=_symbol_span(node),
        sig_tokens=_leaf_tokens(node, _COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _rust_test_macro_name(node: Node) -> str | None:
    """The macro's name if `node` is a `<name>! {...}` invocation of a
    recognized test-generating macro (`_TEST_MACRO_NAMES`), else None."""
    if node.type != "macro_invocation":
        return None
    name = child_text(node.child_by_field_name("macro"))
    return name if name in _TEST_MACRO_NAMES else None


def _macro_symbol(
    node: Node, stack: tuple[str, ...], doc: str, macro_name: str
) -> RawSymbol:
    """A bindable stand-in `RawSymbol` for a test-generating macro block
    (T-0318): its qualname carries `_MACRO_SYMBOL_SUFFIX` so gates can tell
    it apart from a real fn and resolve its `frob:tests` edges against any
    cargo-collected case under the same file/module, since the macro's own
    expanded `#[test]` fns have no literal AST node to bind precisely to."""
    return RawSymbol(
        qualname=".".join((*stack, f"{macro_name}{_MACRO_SYMBOL_SUFFIX}")),
        kind=SymbolKind.FUNCTION,
        public=False,
        span=_symbol_span(node),
        sig_tokens=_leaf_tokens(node, _COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _visit(
    container: Node,
    stack: tuple[str, ...],
    symbols: list[RawSymbol],
    in_impl: bool,
    in_pyo3_impl: bool = False,
) -> None:
    """Recursive descent appending rust symbols under `container`."""
    for node in container.children:
        doc = _leading_doc_comment(node, _COMMENT_TYPES)
        if node.type == "function_item":
            symbols.append(_function_symbol(node, stack, in_impl, in_pyo3_impl, doc))
        elif node.type in ("struct_item", "trait_item"):
            symbols.append(_named_symbol(node, stack, SymbolKind.CLASS, doc))
            _recurse_trait(node, stack, symbols)
        elif node.type in ("enum_item", "type_item"):
            symbols.append(_named_symbol(node, stack, SymbolKind.TYPE, doc))
        elif node.type in ("const_item", "static_item"):
            symbols.append(_named_symbol(node, stack, SymbolKind.CONST, doc))
        elif node.type == "impl_item":
            _recurse_impl(node, stack, symbols)
        elif node.type == "mod_item":
            _recurse_mod(node, stack, symbols, in_impl)
        elif (macro_name := _rust_test_macro_name(node)) is not None:
            symbols.append(_macro_symbol(node, stack, doc, macro_name))


def _recurse_trait(
    node: Node, stack: tuple[str, ...], symbols: list[RawSymbol]
) -> None:
    """Descend into a trait's body (its methods are members)."""
    if node.type != "trait_item":
        return
    body = node.child_by_field_name("body")
    if body is not None:
        name = child_text(node.child_by_field_name("name"))
        _visit(body, (*stack, name), symbols, in_impl=True)


def _recurse_impl(node: Node, stack: tuple[str, ...], symbols: list[RawSymbol]) -> None:
    """Descend into an impl block, propagating `#[pymethods]` export status."""
    name = child_text(node.child_by_field_name("type"))
    body = node.child_by_field_name("body")
    if body is not None:
        _visit(
            body,
            (*stack, name),
            symbols,
            in_impl=True,
            in_pyo3_impl=_rust_pyo3_export(node),
        )


def _recurse_mod(
    node: Node, stack: tuple[str, ...], symbols: list[RawSymbol], in_impl: bool
) -> None:
    """Descend into a module body."""
    name = child_text(node.child_by_field_name("name"))
    body = node.child_by_field_name("body")
    if body is not None:
        _visit(body, (*stack, name), symbols, in_impl)


def _walk_rust(root: Node) -> tuple[RawSymbol, ...]:
    """Every rust symbol (functions, structs, traits, enums, types, consts,
    plus a non-public stand-in per recognized test-generating macro block --
    see `_macro_symbol`)."""
    symbols: list[RawSymbol] = []
    _visit(root, (), symbols, in_impl=False)
    return tuple(symbols)

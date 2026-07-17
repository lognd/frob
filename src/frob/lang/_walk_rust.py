"""Rust symbol walker (docs/modules/lang.md extraction table).

Rust's `pub` visibility plus PyO3 export attributes (`#[pyfunction]`,
`#[pymethods]`, ...) define the crate's Python-facing public surface; that
publicness logic is kept here. The shared token/span/doc mechanism lives in
`_common.py`.
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    child_text,
    leading_doc_comment,
    leaf_tokens,
    span_of,
)
from frob.lang._models import RawSymbol, SymbolKind

_COMMENT_TYPES = frozenset({"line_comment", "block_comment"})

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
        span=span_of(node),
        sig_tokens=leaf_tokens(node, _COMMENT_TYPES, skip),
        body_tokens=leaf_tokens(body, _COMMENT_TYPES) if body else (),
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
        span=span_of(node),
        sig_tokens=leaf_tokens(node, _COMMENT_TYPES),
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
        doc = leading_doc_comment(node, _COMMENT_TYPES)
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
    """Every rust symbol (functions, structs, traits, enums, types, consts)."""
    symbols: list[RawSymbol] = []
    _visit(root, (), symbols, in_impl=False)
    return tuple(symbols)

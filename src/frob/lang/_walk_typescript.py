"""TypeScript / TSX symbol walker (docs/lang.md extraction table).

TypeScript's `export [default]` publicness and `accessibility_modifier`
method visibility are kept here; the shared token/span/doc mechanism lives
in `_common.py`. TSX reuses this walker unchanged.
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    _body_skip,
    child_text,
    leading_doc_comment,
    leaf_tokens,
    span_of,
)
from frob.lang._models import RawSymbol, SymbolKind

_COMMENT_TYPES = frozenset({"comment"})
_TYPE_DECLS = (
    "interface_declaration",
    "type_alias_declaration",
    "enum_declaration",
)


def _unwrap(node: Node) -> tuple[Node, bool]:
    """Peel `export [default]` off a declaration; return (inner, exported)."""
    if node.type == "export_statement":
        inner = None
        for c in node.children:
            if c.type not in ("export", "default"):
                inner = c
        return (inner or node, True)
    return (node, False)


def _function_symbol(
    node: Node, raw_child: Node, stack: tuple[str, ...], exported: bool, doc: str
) -> RawSymbol | None:
    """A function/method `RawSymbol` for a `function_declaration`, or None."""
    body = node.child_by_field_name("body")
    if body is None:
        return None
    name = child_text(node.child_by_field_name("name"))
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD if stack else SymbolKind.FUNCTION,
        public=exported or bool(stack),
        span=span_of(raw_child),
        sig_tokens=leaf_tokens(node, _COMMENT_TYPES, _body_skip(body)),
        body_tokens=leaf_tokens(body, _COMMENT_TYPES),
        doc_text=doc,
    )


def _class_symbol(
    node: Node, raw_child: Node, stack: tuple[str, ...], exported: bool, doc: str
) -> tuple[RawSymbol, Node, str] | None:
    """`(symbol, body, name)` for a `class_declaration`, or None to skip."""
    body = node.child_by_field_name("body")
    if body is None:
        return None
    name = child_text(node.child_by_field_name("name"))
    symbol = RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CLASS,
        public=exported,
        span=span_of(raw_child),
        sig_tokens=leaf_tokens(node, _COMMENT_TYPES, _body_skip(body)),
        body_tokens=(),
        doc_text=doc,
    )
    return symbol, body, name


def _method_symbol(
    node: Node, raw_child: Node, stack: tuple[str, ...], doc: str
) -> RawSymbol | None:
    """A class-member method `RawSymbol` honoring `accessibility_modifier`."""
    body = node.child_by_field_name("body")
    if body is None:
        return None
    name = child_text(node.child_by_field_name("name"))
    access = next(
        (child_text(c) for c in node.children if c.type == "accessibility_modifier"),
        "public",
    )
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD,
        public=access == "public",
        span=span_of(raw_child),
        sig_tokens=leaf_tokens(node, _COMMENT_TYPES, _body_skip(body)),
        body_tokens=leaf_tokens(body, _COMMENT_TYPES),
        doc_text=doc,
    )


def _const_symbol(
    node: Node, raw_child: Node, exported: bool, doc: str
) -> RawSymbol | None:
    """A top-level `lexical_declaration` constant `RawSymbol`, or None."""
    declarator = next(
        (c for c in node.named_children if c.type == "variable_declarator"),
        None,
    )
    if declarator is None:
        return None
    name = child_text(declarator.child_by_field_name("name"))
    if not name:
        return None
    return RawSymbol(
        qualname=name,
        kind=SymbolKind.CONST,
        public=exported,
        span=span_of(raw_child),
        sig_tokens=leaf_tokens(node, _COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _type_symbol(
    node: Node, raw_child: Node, exported: bool, doc: str
) -> RawSymbol | None:
    """An interface/type-alias/enum `RawSymbol`, or None if unnamed."""
    name = child_text(node.child_by_field_name("name"))
    if not name:
        return None
    return RawSymbol(
        qualname=name,
        kind=SymbolKind.TYPE,
        public=exported,
        span=span_of(raw_child),
        sig_tokens=leaf_tokens(node, _COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _visit(container: Node, stack: tuple[str, ...], symbols: list[RawSymbol]) -> None:
    """Recursive descent appending TypeScript symbols under `container`."""
    for raw_child in container.children:
        node, exported = _unwrap(raw_child)
        doc = leading_doc_comment(raw_child, _COMMENT_TYPES)
        if node.type == "function_declaration":
            _append(symbols, _function_symbol(node, raw_child, stack, exported, doc))
        elif node.type == "class_declaration":
            built = _class_symbol(node, raw_child, stack, exported, doc)
            if built is not None:
                symbol, body, name = built
                symbols.append(symbol)
                _visit(body, (*stack, name), symbols)
        elif node.type == "method_definition" and stack:
            _append(symbols, _method_symbol(node, raw_child, stack, doc))
        elif node.type == "lexical_declaration" and not stack:
            _append(symbols, _const_symbol(node, raw_child, exported, doc))
        elif node.type in _TYPE_DECLS and not stack:
            _append(symbols, _type_symbol(node, raw_child, exported, doc))


def _append(symbols: list[RawSymbol], symbol: RawSymbol | None) -> None:
    """Append `symbol` to `symbols` when it is not None."""
    if symbol is not None:
        symbols.append(symbol)


def _walk_typescript(root: Node) -> tuple[RawSymbol, ...]:
    """Every TypeScript symbol (functions, classes, methods, consts, types)."""
    symbols: list[RawSymbol] = []
    _visit(root, (), symbols)
    return tuple(symbols)

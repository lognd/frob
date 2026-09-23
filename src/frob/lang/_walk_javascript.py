"""JavaScript / JSX symbol walker (T-5300, WEBSEC web-app-lint substrate leaf).

WEBSEC/A11Y/SEO rules in the `T-5140` web-app epic need `.js`/`.jsx` files
to reach `frob.lang.parse_file` instead of returning
`LangError.UnsupportedLanguage` -- this module is that wiring's walker
half, wired alongside `frob.lang.__init__`'s `_EXTENSION_TABLE` and
`frob.lang._extract`'s `_WALKERS`/`COMMENT_TYPES` dispatch tables (both
edited alongside this module -- see
docs/modules/lang.md#per-language-walker-notes). Mirrors
`_walk_typescript.py`'s shape (`.jsx` reuses this walker unchanged, the
same way `.tsx` reuses `_walk_typescript`) but drops TypeScript-only node
kinds (`interface_declaration`/`type_alias_declaration`/`enum_declaration`,
`accessibility_modifier`) that the plain `javascript` grammar never emits.

WHAT COUNTS AS A SYMBOL: this walker does not attempt full symbol-tree
fidelity -- most rules in this epic query raw nodes via
`frob.lang.raw_tree`/`symbol_tree`, not `frob.graph` symbol qualnames
(`_walk_typescript.py`'s own docstring makes the identical point for
TS/TSX), so a thin walk covering the common declaration shapes
(`function_declaration`, `class_declaration` + its `method_definition`
members, top-level `lexical_declaration` constants, all honoring
`export [default]` publicness) is enough to make `parse_file` succeed and
produce a non-empty tree (this ticket's positive control).
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    _body_skip,
    _canonical_tokens,
    _child_text,
    _leading_doc_comment,
    _leaf_tokens,
    _span_of,
)
from frob.lang._models import RawSymbol, SymbolKind

_COMMENT_TYPES = frozenset({"comment"})


# frob:waive DUP001 reason="same export_statement-peel shape as _walk_typescript.py's \
# _unwrap by grammar coincidence, not shared code -- see T-5300"
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
    name = _child_text(node.child_by_field_name("name"))
    if not name:
        return None
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD if stack else SymbolKind.FUNCTION,
        public=exported or bool(stack),
        span=_span_of(raw_child),
        sig_tokens=_leaf_tokens(node, _COMMENT_TYPES, _body_skip(body)),
        body_tokens=_leaf_tokens(body, _COMMENT_TYPES),
        doc_text=doc,
        body_norm=_canonical_tokens(body, _COMMENT_TYPES),
    )


def _class_symbol(
    node: Node, raw_child: Node, stack: tuple[str, ...], exported: bool, doc: str
) -> tuple[RawSymbol, Node, str] | None:
    """`(symbol, body, name)` for a `class_declaration`, or None to skip."""
    body = node.child_by_field_name("body")
    if body is None:
        return None
    name = _child_text(node.child_by_field_name("name"))
    if not name:
        return None
    symbol = RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CLASS,
        public=exported,
        span=_span_of(raw_child),
        sig_tokens=_leaf_tokens(node, _COMMENT_TYPES, _body_skip(body)),
        body_tokens=(),
        doc_text=doc,
    )
    return symbol, body, name


def _method_symbol(
    node: Node, raw_child: Node, stack: tuple[str, ...], doc: str
) -> RawSymbol | None:
    """A class-member method `RawSymbol` (JS has no `accessibility_modifier`
    keyword -- every method is always public, unlike TypeScript's walker)."""
    body = node.child_by_field_name("body")
    if body is None:
        return None
    name = _child_text(node.child_by_field_name("name"))
    if not name:
        return None
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD,
        public=True,
        span=_span_of(raw_child),
        sig_tokens=_leaf_tokens(node, _COMMENT_TYPES, _body_skip(body)),
        body_tokens=_leaf_tokens(body, _COMMENT_TYPES),
        doc_text=doc,
        body_norm=_canonical_tokens(body, _COMMENT_TYPES),
    )


# frob:waive DUP001 reason="same rationale as _unwrap's waiver above -- see T-5300"
# frob:waive DUP002 reason="RawSymbol-constructor field list repeating, not real \
# shared behavior with _walk_css.py::_css_rule_symbol -- see T-5300"
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
    name = _child_text(declarator.child_by_field_name("name"))
    if not name:
        return None
    return RawSymbol(
        qualname=name,
        kind=SymbolKind.CONST,
        public=exported,
        span=_span_of(raw_child),
        sig_tokens=_leaf_tokens(node, _COMMENT_TYPES),
        body_tokens=(),
        doc_text=doc,
    )


def _visit(container: Node, stack: tuple[str, ...], symbols: list[RawSymbol]) -> None:
    """Recursive descent appending JavaScript symbols under `container`."""
    for raw_child in container.children:
        node, exported = _unwrap(raw_child)
        doc = _leading_doc_comment(raw_child, _COMMENT_TYPES)
        if node.type == "function_declaration":
            _append(symbols, _function_symbol(node, raw_child, stack, exported, doc))
        elif node.type == "class_declaration":
            built = _class_symbol(node, raw_child, stack, exported, doc)
            if built is not None:
                symbol, body, name = built
                symbols.append(symbol)
                # frob:invariant terminates reason="body is derived from node's class body field by _class_symbol, and node is a child of container, so body is a proper descendant of container in the finite tree-sitter parse tree" measure="container's subtree depth strictly decreases"  # noqa: E501
                _visit(body, (*stack, name), symbols)
        elif node.type == "method_definition" and stack:
            _append(symbols, _method_symbol(node, raw_child, stack, doc))
        elif node.type == "lexical_declaration" and not stack:
            _append(symbols, _const_symbol(node, raw_child, exported, doc))


def _append(symbols: list[RawSymbol], symbol: RawSymbol | None) -> None:
    """Append `symbol` to `symbols` when it is not None."""
    if symbol is not None:
        symbols.append(symbol)


# frob:ticket T-5300
def _walk_javascript(root: Node) -> tuple[RawSymbol, ...]:
    """Every JavaScript symbol (functions, classes, methods, top-level
    consts), reused unchanged for `.jsx` -- mirrors `_walk_typescript`."""
    symbols: list[RawSymbol] = []
    _visit(root, (), symbols)
    return tuple(symbols)

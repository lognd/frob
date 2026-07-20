"""C / C++ symbol walker (docs/modules/lang.md extraction table).

C/C++ publicness rules (file-scope `static` for free functions, `access_specifier`
for class members) and out-of-line `Class::method` declarator naming are kept
here; the shared token/span/doc mechanism lives in `_common.py`. Both C and
C++ share this walker, differing only in their comment-node-type set, which
is threaded through the walk in a `_Ctx` (never a module global -- the parser
runs under `frob.check`'s thread pool).
"""

# frob:waive TEST005 reason="module line coverage 69.9%, debt T-0160"
# frob:waive REF002 reason="private per-language walker imported only by its sibling aggregator frob.lang._extract; a single inbound anchor is intentional for a language-dispatch leaf module, T-0450"  # noqa: E501

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node

from frob.lang._common import (
    _body_skip,
    _leading_doc_comment,
    _leaf_tokens,
    _span_of,
    child_text,
)
from frob.lang._models import RawSymbol, SymbolKind


@dataclass(frozen=True)
class _Ctx:
    """Per-walk state: the grammar's comment-node types and the symbol sink."""

    comment_types: frozenset[str]
    symbols: list[RawSymbol]


def _find_declarator_name(node: Node) -> str:
    """Descend through pointer/function declarators to the innermost identifier.

    An out-of-line method definition's declarator (`Widget::draw`) is a
    `qualified_identifier`, not a bare `identifier` -- its own text (with
    the `::` scope kept intact) is the name, not the trailing segment,
    otherwise `Widget::draw` and an unrelated top-level `draw` would
    collapse to the same qualname.
    """
    cur = node
    while cur is not None:
        if cur.type == "qualified_identifier":
            return child_text(cur)
        if cur.type in ("identifier", "field_identifier", "type_identifier"):
            return child_text(cur)
        inner = cur.child_by_field_name("declarator")
        if inner is None:
            for c in cur.children:
                if c.type in ("identifier", "field_identifier"):
                    return child_text(c)
            return ""
        cur = inner
    return ""


def _has_static(node: Node) -> bool:
    """True if `node` carries a file-scope `static` storage-class specifier."""
    return any(
        c.type == "storage_class_specifier" and child_text(c) == "static"
        for c in node.children
    )


def _function_symbol(
    ctx: _Ctx, node: Node, stack: tuple[str, ...], cur_access: str, doc: str
) -> RawSymbol:
    """A function/method `RawSymbol`; member publicness follows `cur_access`."""
    declarator = node.child_by_field_name("declarator")
    name = _find_declarator_name(declarator) if declarator else ""
    body = node.child_by_field_name("body")
    skip = ((body.start_byte, body.end_byte),) if body else ()
    public = (cur_access != "private") if stack else not _has_static(node)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD if stack else SymbolKind.FUNCTION,
        public=public,
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, ctx.comment_types, skip),
        body_tokens=_leaf_tokens(body, ctx.comment_types) if body else (),
        doc_text=doc,
    )


def _class_symbol(
    ctx: _Ctx, node: Node, stack: tuple[str, ...], doc: str
) -> tuple[RawSymbol, Node, str] | None:
    """`(symbol, body, default_access)` for a class/struct, or None to skip."""
    body = node.child_by_field_name("body")
    if body is None:
        return None
    name = child_text(node.child_by_field_name("name"))
    if not name:
        return None
    symbol = RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CLASS,
        public=not _has_static(node),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, ctx.comment_types, _body_skip(body)),
        body_tokens=(),
        doc_text=doc,
    )
    default_access = "private" if node.type == "class_specifier" else "public"
    return symbol, body, default_access


def _enum_symbol(
    ctx: _Ctx, node: Node, stack: tuple[str, ...], doc: str
) -> RawSymbol | None:
    """An enum `RawSymbol`, or None if the enum is anonymous."""
    if node.child_by_field_name("name") is None:
        return None
    name = child_text(node.child_by_field_name("name"))
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.TYPE,
        public=True,
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, ctx.comment_types),
        body_tokens=(),
        doc_text=doc,
    )


def _typedef_name(node: Node) -> str:
    """The declared name of a `type_definition`/`alias_declaration` node."""
    name_node = node.child_by_field_name("name") or node.child_by_field_name("type")
    name = _find_declarator_name(node) if name_node is None else child_text(name_node)
    if name:
        return name
    for c in node.children:
        if c.type == "type_identifier":
            name = child_text(c)
    return name


def _type_symbol(ctx: _Ctx, node: Node, doc: str) -> RawSymbol | None:
    """A typedef/alias `RawSymbol`, or None if no name can be recovered."""
    name = _typedef_name(node)
    if not name:
        return None
    return RawSymbol(
        qualname=name,
        kind=SymbolKind.TYPE,
        public=True,
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, ctx.comment_types),
        body_tokens=(),
        doc_text=doc,
    )


def _has_const_qualifier(node: Node) -> bool:
    """True if `node` carries a `const` type qualifier."""
    return any(
        c.type == "type_qualifier" and child_text(c) == "const" for c in node.children
    )


def _const_symbol(ctx: _Ctx, node: Node, doc: str) -> RawSymbol | None:
    """A file-scope `const` declaration `RawSymbol`, or None if not one."""
    if not _has_const_qualifier(node):
        return None
    init = next((c for c in node.children if c.type == "init_declarator"), None)
    if init is None:
        return None
    name_node = init.child_by_field_name("declarator")
    name = _find_declarator_name(name_node) if name_node else ""
    if not name:
        return None
    return RawSymbol(
        qualname=name,
        kind=SymbolKind.CONST,
        public=not _has_static(node),
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, ctx.comment_types),
        body_tokens=(),
        doc_text=doc,
    )


def _dispatch(ctx: _Ctx, node: Node, stack: tuple[str, ...], cur_access: str) -> None:
    """Build and append the symbol(s) for one C/C++ child node."""
    doc = _leading_doc_comment(node, ctx.comment_types)
    if node.type == "function_definition":
        ctx.symbols.append(_function_symbol(ctx, node, stack, cur_access, doc))
    elif node.type in ("class_specifier", "struct_specifier"):
        built = _class_symbol(ctx, node, stack, doc)
        if built is not None:
            symbol, body, default_access = built
            ctx.symbols.append(symbol)
            name = child_text(node.child_by_field_name("name"))
            _visit(ctx, body, (*stack, name), default_access)
    elif node.type == "enum_specifier":
        _append(ctx, _enum_symbol(ctx, node, stack, doc))
    elif node.type in ("type_definition", "alias_declaration") and not stack:
        _append(ctx, _type_symbol(ctx, node, doc))
    elif node.type == "declaration" and not stack:
        _append(ctx, _const_symbol(ctx, node, doc))
    elif node.type == "namespace_definition":
        _recurse_namespace(ctx, node, stack)


def _recurse_namespace(ctx: _Ctx, node: Node, stack: tuple[str, ...]) -> None:
    """Descend into a namespace body, extending the qualname stack if named."""
    name = child_text(node.child_by_field_name("name"))
    body = node.child_by_field_name("body")
    if body is not None:
        _visit(ctx, body, (*stack, name) if name else stack, "public")


def _append(ctx: _Ctx, symbol: RawSymbol | None) -> None:
    """Append `symbol` to the context's sink when it is not None."""
    if symbol is not None:
        ctx.symbols.append(symbol)


def _visit(ctx: _Ctx, container: Node, stack: tuple[str, ...], access: str) -> None:
    """Recursive descent appending C/C++ symbols, threading member access."""
    cur_access = access
    for node in container.children:
        if node.type == "access_specifier":
            cur_access = child_text(node)
            continue
        _dispatch(ctx, node, stack, cur_access)


def _walk_c_family(root: Node, comment_types: frozenset[str]) -> tuple[RawSymbol, ...]:
    """Every C/C++ symbol (functions, methods, classes, enums, typedefs, consts)."""
    ctx = _Ctx(comment_types=comment_types, symbols=[])
    _visit(ctx, root, (), "public")
    return tuple(ctx.symbols)

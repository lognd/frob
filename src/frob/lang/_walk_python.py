"""Python symbol walker (docs/modules/lang.md extraction table).

Python's declaration vocabulary (docstring-as-first-statement,
`decorated_definition` wrappers, SCREAMING_CASE module constants) is kept
here; the shared token/span/doc mechanism lives in `_common.py`.
"""

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    ByteRange,
    _body_skip,
    child_text,
    collapse_ws,
    leaf_tokens,
    span_of,
)
from frob.lang._models import RawSymbol, SymbolKind

_COMMENT_TYPES = frozenset({"comment"})
_DEF_TYPES = ("function_definition", "class_definition")
_NESTED_TYPES = ("function_definition", "class_definition", "decorated_definition")


def _python_docstring(body: Node) -> tuple[str, ByteRange | None]:
    """The collapsed docstring text and its byte range for a def/class body."""
    if body.named_child_count == 0:
        return "", None
    first = body.named_children[0]
    if first.type == "expression_statement":
        if first.named_child_count == 0 or first.named_children[0].type != "string":
            return "", None
        string_node = first.named_children[0]
        doc_range = (first.start_byte, first.end_byte)
    elif first.type == "string":
        string_node = first
        doc_range = (first.start_byte, first.end_byte)
    else:
        return "", None
    content = "".join(
        child_text(c) for c in string_node.children if c.type == "string_content"
    )
    return collapse_ws(content), doc_range


def _effective_node(child: Node) -> tuple[Node, Node] | None:
    """`(node, sig_node)` peeling a `decorated_definition`, or None to skip."""
    if child.type != "decorated_definition":
        return child, child
    inner = next((c for c in child.children if c.type in _DEF_TYPES), None)
    if inner is None:
        return None
    return inner, child


def _function_symbol(
    node: Node, sig_node: Node, stack: tuple[str, ...], body: Node
) -> RawSymbol:
    """A function/method `RawSymbol` (method when nested inside a class)."""
    name = child_text(node.child_by_field_name("name"))
    doc, doc_range = _python_docstring(body)
    sig_tokens = leaf_tokens(sig_node, _COMMENT_TYPES, _body_skip(body))
    body_skip_range = (doc_range,) if doc_range else ()
    body_tokens = leaf_tokens(body, _COMMENT_TYPES, body_skip_range)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD if stack else SymbolKind.FUNCTION,
        public=not name.startswith("_"),
        span=span_of(sig_node),
        sig_tokens=sig_tokens,
        body_tokens=body_tokens,
        doc_text=doc,
    )


def _class_symbol(
    node: Node, sig_node: Node, stack: tuple[str, ...], name: str, body: Node
) -> RawSymbol:
    """A class `RawSymbol`; nested defs are excluded from its body tokens."""
    doc, doc_range = _python_docstring(body)
    sig_tokens = leaf_tokens(sig_node, _COMMENT_TYPES, _body_skip(body))
    nested_ranges = tuple(
        (c.start_byte, c.end_byte) for c in body.children if c.type in _NESTED_TYPES
    )
    body_skip_ranges = nested_ranges + ((doc_range,) if doc_range else ())
    body_tokens = leaf_tokens(body, _COMMENT_TYPES, body_skip_ranges)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CLASS,
        public=not name.startswith("_"),
        span=span_of(sig_node),
        sig_tokens=sig_tokens,
        body_tokens=body_tokens,
        doc_text=doc,
    )


def _const_symbol(node: Node) -> RawSymbol | None:
    """A module-level SCREAMING_CASE constant `RawSymbol`, or None if not one.

    `node` is either an `assignment` itself (the grammar shipped by
    tree-sitter-language-pack emits top-level assignments as direct
    `module` children) or an `expression_statement` wrapping one (older/
    other grammar builds) -- both forms are accepted so a right-hand side
    of any kind, literal or call expression (`X = Foo(...)`), is caught.
    """
    name = _const_assignment_name(node)
    if name is None:
        return None
    return RawSymbol(
        qualname=name,
        kind=SymbolKind.CONST,
        public=not name.startswith("_"),
        span=span_of(node),
        sig_tokens=leaf_tokens(node, _COMMENT_TYPES),
        body_tokens=(),
        doc_text="",
    )


def _const_assignment_name(node: Node) -> str | None:
    """The SCREAMING_CASE target name of a module-level constant assignment
    `node`, or None if it doesn't match that shape."""
    assign = (
        node
        if node.type == "assignment"
        else (node.named_children[0] if node.named_child_count else None)
    )
    if assign is None or assign.type != "assignment":
        return None
    left = assign.child_by_field_name("left")
    if left is None or left.type != "identifier":
        return None
    name = child_text(left)
    if not (name and (name.isupper() or "_" in name) and name[0].isalpha()):
        return None
    if not name.replace("_", "").isupper():
        return None
    return name


def _visit(container: Node, stack: tuple[str, ...], symbols: list[RawSymbol]) -> None:
    """Recursive descent appending python symbols under `container`."""
    for child in container.children:
        effective = _effective_node(child)
        if effective is None:
            continue
        node, sig_node = effective
        if node.type == "function_definition":
            body = node.child_by_field_name("body")
            if body is not None:
                symbols.append(_function_symbol(node, sig_node, stack, body))
        elif node.type == "class_definition":
            body = node.child_by_field_name("body")
            if body is None:
                continue
            name = child_text(node.child_by_field_name("name"))
            symbols.append(_class_symbol(node, sig_node, stack, name, body))
            _visit(body, (*stack, name), symbols)
        elif node.type in ("expression_statement", "assignment") and not stack:
            const = _const_symbol(node)
            if const is not None:
                symbols.append(const)


def _walk_python(root: Node) -> tuple[RawSymbol, ...]:
    """Every python symbol (functions, methods, classes, module constants)."""
    symbols: list[RawSymbol] = []
    _visit(root, (), symbols)
    return tuple(symbols)

"""Python symbol walker (docs/modules/lang.md extraction table).

Python's declaration vocabulary (docstring-as-first-statement,
`decorated_definition` wrappers, SCREAMING_CASE module constants) is kept
here; the shared token/span/doc mechanism lives in `_common.py`.
"""

# frob:waive REF002 reason="private per-language walker imported only by its sibling aggregator frob.lang._extract; a single inbound anchor is intentional for a language-dispatch leaf module, T-0450"  # noqa: E501

from __future__ import annotations

from tree_sitter import Node

from frob.lang._common import (
    ByteRange,
    _body_skip,
    _canonical_tokens,
    _collapse_ws,
    _find_enclosing_symbol,
    _leaf_tokens,
    _span_of,
    child_text,
)
from frob.lang._models import RawComment, RawSymbol, SymbolKind

_COMMENT_TYPES = frozenset({"comment"})
_DEF_TYPES = ("function_definition", "class_definition")
_NESTED_TYPES = ("function_definition", "class_definition", "decorated_definition")


def _docstring_string_node(body: Node) -> Node | None:
    """The leading-statement `string` node holding `body`'s docstring, if
    any -- shared by `_python_docstring` (digest text) and
    `_docstring_nodes` (frob: directive scan, T-0342) so the "what counts
    as a docstring" rule lives in exactly one place."""
    if body.named_child_count == 0:
        return None
    first = body.named_children[0]
    if first.type == "expression_statement":
        if first.named_child_count == 0 or first.named_children[0].type != "string":
            return None
        return first.named_children[0]
    if first.type == "string":
        return first
    return None


def _python_docstring(body: Node) -> tuple[str, ByteRange | None]:
    """The collapsed docstring text and its byte range for a def/class body."""
    string_node = _docstring_string_node(body)
    if string_node is None:
        return "", None
    content = "".join(
        child_text(c) for c in string_node.children if c.type == "string_content"
    )
    return _collapse_ws(content), (string_node.start_byte, string_node.end_byte)


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
    sig_tokens = _leaf_tokens(sig_node, _COMMENT_TYPES, _body_skip(body))
    body_skip_range = (doc_range,) if doc_range else ()
    body_tokens = _leaf_tokens(body, _COMMENT_TYPES, body_skip_range)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.METHOD if stack else SymbolKind.FUNCTION,
        public=not name.startswith("_"),
        span=_span_of(sig_node),
        sig_tokens=sig_tokens,
        body_tokens=body_tokens,
        doc_text=doc,
        body_norm=_canonical_tokens(body, _COMMENT_TYPES, body_skip_range),
    )


def _class_symbol(
    node: Node, sig_node: Node, stack: tuple[str, ...], name: str, body: Node
) -> RawSymbol:
    """A class `RawSymbol`; nested defs are excluded from its body tokens."""
    doc, doc_range = _python_docstring(body)
    sig_tokens = _leaf_tokens(sig_node, _COMMENT_TYPES, _body_skip(body))
    nested_ranges = tuple(
        (c.start_byte, c.end_byte) for c in body.children if c.type in _NESTED_TYPES
    )
    body_skip_ranges = nested_ranges + ((doc_range,) if doc_range else ())
    body_tokens = _leaf_tokens(body, _COMMENT_TYPES, body_skip_ranges)
    return RawSymbol(
        qualname=".".join((*stack, name)),
        kind=SymbolKind.CLASS,
        public=not name.startswith("_"),
        span=_span_of(sig_node),
        sig_tokens=sig_tokens,
        body_tokens=body_tokens,
        doc_text=doc,
        body_norm=_canonical_tokens(body, _COMMENT_TYPES, body_skip_ranges),
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
        span=_span_of(node),
        sig_tokens=_leaf_tokens(node, _COMMENT_TYPES),
        body_tokens=(),
        doc_text="",
    )


# frob:ticket T-0565
def _const_assignment_name(node: Node) -> str | None:
    """The SCREAMING_CASE target name of a module-level constant assignment
    `node`, or None if it doesn't match that shape.

    T-0565: a leading underscore (`_DISPATCH_BY_TYPE`, a PRIVATE module
    dispatch-table constant) is now accepted -- the previous
    `name[0].isalpha()` check rejected any name starting with `_`, which
    meant a private constant assignment was never turned into a `RawSymbol`
    at all (not merely under-recalled: invisible to `_visit`, so its own
    right-hand-side tokens -- e.g. `{"cpp": _dispatch_check_cpp, ...}` --
    were silently dropped from the whole file's symbol list). That, not a
    `build_reference_graph` recall gap, was the actual root cause behind
    most of DEAD001's T-0422/T-0565 dispatch-table false-positive class:
    the referencing statement was never parsed into anything a reference
    graph could scan in the first place. `name.lstrip("_")` restores the
    "starts with a letter, once underscores are stripped" shape check
    without excluding a private name outright."""
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
    bare = name.lstrip("_") if name else ""
    if not (name and bare and (name.isupper() or "_" in name) and bare[0].isalpha()):
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
            # frob:invariant terminates reason="body is node's own 'body' field child, and node is a child of container, so body is a proper descendant of container in the finite tree-sitter parse tree" measure="container's subtree depth strictly decreases"  # noqa: E501
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


def _docstring_nodes(container: Node) -> list[Node]:
    """Depth-first collect every leading-statement docstring `string` node
    under `container` (the module root, or any def/class body), recursing
    only into nested function/class bodies -- matches `_visit`'s descent
    shape without needing its qualname stack, since docstring binding is
    resolved later by span alone (`_find_enclosing_symbol`)."""
    nodes: list[Node] = []
    own = _docstring_string_node(container)
    if own is not None:
        nodes.append(own)
    for child in container.children:
        effective = _effective_node(child)
        if effective is None:
            continue
        node, _sig_node = effective
        if node.type in _DEF_TYPES:
            body = node.child_by_field_name("body")
            if body is not None:
                # frob:invariant terminates reason="body is node's own 'body' field child, and node is a child of container, so body is a proper descendant of container in the finite tree-sitter parse tree" measure="container's subtree depth strictly decreases"  # noqa: E501
                nodes.extend(_docstring_nodes(body))
    return nodes


def _walk_python_docstring_comments(
    root: Node, symbols: tuple[RawSymbol, ...]
) -> tuple[RawComment, ...]:
    """`RawComment` for every module/class/function docstring (T-0342).

    Without this, a `frob:` directive written inside a docstring instead of
    a `#` comment is silently invisible to `frob.graph`'s DSL parser -- no
    edge, no `MalformedDirective` either (see this module's `RawComment`
    docstring for what `frob.graph.dsl.parse_directives` does with these).
    Each docstring binds to the symbol whose body it opens (module-level
    when nothing encloses it, resolved via `_find_enclosing_symbol` exactly
    like a comment directive would), never to a `following` symbol -- a
    docstring is never "about" whatever comes after the def it lives in.
    """
    comments: list[RawComment] = []
    for node in _docstring_nodes(root):
        content = "".join(
            child_text(c) for c in node.children if c.type == "string_content"
        )
        span = _span_of(node)
        enclosing = _find_enclosing_symbol(span, symbols)
        comments.append(
            RawComment(text=content, span=span, enclosing=enclosing, following=None)
        )
    return tuple(comments)

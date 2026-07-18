"""Python fingerprinting + function iteration for the legacy dup scan.

Local-name collection (for alpha-renaming) and body serialization, plus the
function-node walker `_scan_py_file` drives. Every walker keeps its
recursion shallow by delegating each statement/parameter shape to a small
handler rather than nesting the branches inline.
"""

from __future__ import annotations

from collections.abc import Iterator

from tree_sitter import Node

from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text


def _collect_locals_py(func_node: Node) -> set[str]:
    """Collect identifiers that are local to a Python function."""
    locals_: set[str] = set()
    params = _child(func_node, "parameters")
    if params:
        _collect_param_names(params, locals_)
    body = _child(func_node, "body")
    if body:
        _collect_assigned_names(body, locals_)
    return locals_


def _first_identifier(node: Node) -> str | None:
    """The text of the first `identifier` _child of `node`, or None."""
    for c in node.named_children:
        if c.type == "identifier":
            return _node_text(c)
    return None


def _harvest_param(child_node: Node, out: set[str]) -> None:
    """Add the bound name(s) of one parameter node to `out`."""
    t = child_node.type
    if t == "identifier":
        out.add(_node_text(child_node))
    elif t in ("default_parameter", "typed_parameter", "typed_default_parameter"):
        name_node = child_node.child_by_field_name("name")
        if name_node:
            out.add(_node_text(name_node))
        else:
            name = _first_identifier(child_node)
            if name is not None:
                out.add(name)
    elif t in ("list_splat_pattern", "dictionary_splat_pattern"):
        name = _first_identifier(child_node)
        if name is not None:
            out.add(name)


def _collect_param_names(node: Node, out: set[str]) -> None:
    """Harvest every parameter binding name under a `parameters` node."""
    for c in node.named_children:
        _harvest_param(c, out)


def _harvest_assignment(inner: Node, out: set[str]) -> None:
    """Add the LHS binding names of an `assignment`/`augmented_assignment`."""
    if inner.type == "assignment":
        lhs = inner.child_by_field_name("left")
        if lhs:
            _harvest_pattern(lhs, out)
    elif inner.type == "augmented_assignment":
        lhs = inner.child_by_field_name("left")
        if lhs and lhs.type == "identifier":
            out.add(_node_text(lhs))


def _harvest_binding_stmt(child_node: Node, out: set[str]) -> None:
    """Add binding names from one statement node, recursing into nested
    blocks. Names in nested function/class scopes are deliberately skipped."""
    t = child_node.type
    if t == "expression_statement":
        for inner in child_node.children:
            _harvest_assignment(inner, out)
    elif t in ("assignment", "augmented_assignment"):
        _harvest_assignment(child_node, out)
    elif t in ("for_statement", "async_for_statement"):
        left = child_node.child_by_field_name("left")
        if left:
            _harvest_pattern(left, out)
        body = child_node.child_by_field_name("body")
        if body:
            _collect_assigned_names(body, out)
    elif t == "with_statement":
        _harvest_with(child_node, out)
    elif t in ("if_statement", "while_statement", "try_statement", "block", "suite"):
        _collect_assigned_names(child_node, out)


def _harvest_with(child_node: Node, out: set[str]) -> None:
    """Add `with ... as <name>` binding names and recurse into the body."""
    for item in child_node.named_children:
        if item.type == "with_item":
            alias = item.child_by_field_name("alias")
            if alias:
                _harvest_pattern(alias, out)
    body = child_node.child_by_field_name("body")
    if body:
        _collect_assigned_names(body, out)


def _collect_assigned_names(node: Node, out: set[str]) -> None:
    """Walk the body and harvest assignment/for/with binding names."""
    for c in node.children:
        _harvest_binding_stmt(c, out)


def _harvest_pattern(node: Node, out: set[str]) -> None:
    """Add every identifier name in an assignment-target pattern to `out`."""
    if node.type == "identifier":
        out.add(_node_text(node))
    else:
        for c in node.named_children:
            _harvest_pattern(c, out)


_STRING_LEAF_TYPES = frozenset(
    {"string", "string_content", "interpolation", "concatenated_string"}
)


def _serialize_py_body(body: Node, locals_: set[str]) -> str:
    """Serialize a Python body node to a normalized token string."""
    mapping: dict[str, str] = {}
    tokens: list[str] = []

    def visit(n: Node) -> None:
        if n.type == "comment":
            return
        if not n.children:
            tokens.append(_leaf_token(n, locals_, mapping))
            return
        if n.type in ("string", "concatenated_string"):
            tokens.append("_S_")
            return
        for c in n.children:
            visit(c)

    visit(body)
    return " ".join(tokens)


def _leaf_token(n: Node, locals_: set[str], mapping: dict[str, str]) -> str:
    """The normalized token for a leaf node: renamed local, `_S_`/`_N_`
    literal placeholder, or the raw text."""
    t = n.type
    raw = _node_text(n)
    if t == "identifier" and raw in locals_:
        if raw not in mapping:
            mapping[raw] = f"_v{len(mapping)}"
        return mapping[raw]
    if t in _STRING_LEAF_TYPES:
        return "_S_"
    if t in ("integer", "float"):
        return "_N_"
    return raw


def _enclosing_class_py(func_node: Node) -> str | None:
    """Return the enclosing class name for a function node, or None."""
    parent = func_node.parent
    while parent is not None:
        if parent.type == "block":
            grandparent = parent.parent
            if grandparent is not None and grandparent.type == "class_definition":
                name_node = _child(grandparent, "name")
                if name_node:
                    return _node_text(name_node)
        parent = parent.parent
    return None


_PY_FUNC_TYPES = frozenset({"function_definition", "async_function_definition"})


def _iter_functions_py(root_node: Node) -> Iterator[tuple[Node, str]]:
    """Yield `(func_node, symbol)` for all function/async_function nodes,
    including nested ones, `symbol` qualified by enclosing class where any."""
    if root_node.type in _PY_FUNC_TYPES:
        name_node = _child(root_node, "name")
        func_name = _node_text(name_node) if name_node else "<unknown>"
        class_name = _enclosing_class_py(root_node)
        symbol = f"{class_name}.{func_name}" if class_name else func_name
        yield root_node, symbol
    for c in root_node.children:
        yield from _iter_functions_py(c)

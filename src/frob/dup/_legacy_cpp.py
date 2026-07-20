"""C++ fingerprinting + function iteration for the legacy dup scan.

Mirrors `_legacy_py` for the tree-sitter C++ grammar: declarator-name
harvesting for locals, body serialization, and a function-node walker.
"""

# frob:waive TEST005 reason="module line coverage 15.2%, debt T-0160"
# frob:waive REF002 reason="private C++ fingerprinter imported only by its sibling aggregator frob.dup._legacy; a single inbound anchor is intentional for a legacy-scan leaf module, T-0450"  # noqa: E501

from __future__ import annotations

from collections.abc import Iterator

from tree_sitter import Node

from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text


def _collect_locals_cpp(func_node: Node) -> set[str]:
    """Collect identifiers local to a C++ function (params + declarations)."""
    locals_: set[str] = set()
    params = _child(func_node, "parameters")
    if params:
        for c in params.named_children:
            _harvest_cpp_param(c, locals_)
    body = _child(func_node, "body")
    if body:
        _collect_assigned_names_cpp(body, locals_)
    return locals_


def _harvest_cpp_param(node: Node, out: set[str]) -> None:
    """Add the declared name of one C++ parameter node to `out`."""
    if node.type in (
        "parameter_declaration",
        "optional_parameter_declaration",
        "variadic_parameter_declaration",
    ):
        decl = node.child_by_field_name("declarator")
        if decl:
            _harvest_cpp_declarator_name(decl, out)


def _harvest_cpp_declarator_name(node: Node, out: set[str]) -> None:
    """Unwrap pointer/reference declarators to the identifier name(s) inside."""
    if node.type == "identifier":
        out.add(_node_text(node))
    elif node.type in (
        "pointer_declarator",
        "reference_declarator",
        "abstract_pointer_declarator",
    ):
        inner = node.child_by_field_name("declarator")
        if inner:
            _harvest_cpp_declarator_name(inner, out)
    else:
        for c in node.named_children:
            _harvest_cpp_declarator_name(c, out)


def _collect_assigned_names_cpp(node: Node, out: set[str]) -> None:
    """Harvest declaration/for binding names from a C++ statement subtree."""
    for c in node.named_children:
        t = c.type
        if t == "declaration":
            decl = c.child_by_field_name("declarator")
            if decl:
                _harvest_cpp_declarator_name(decl, out)
        elif t in ("for_statement", "for_range_loop"):
            _harvest_cpp_for(c, out)
        elif t in (
            "if_statement",
            "while_statement",
            "do_statement",
            "compound_statement",
            "try_statement",
        ):
            _collect_assigned_names_cpp(c, out)


def _harvest_cpp_for(node: Node, out: set[str]) -> None:
    """Harvest binding names from a C++ for-loop's initializer and body."""
    init = node.child_by_field_name("initializer")
    if init:
        _collect_assigned_names_cpp(init, out)
    body = node.child_by_field_name("body")
    if body:
        _collect_assigned_names_cpp(body, out)


_CPP_STRING_LEAF_TYPES = frozenset(
    {
        "string_literal",
        "raw_string_literal",
        "char_literal",
        "user_defined_string_literal",
    }
)
_CPP_STRING_NODE_TYPES = frozenset(
    {"string_literal", "raw_string_literal", "char_literal"}
)


def _serialize_cpp_body(body: Node, locals_: set[str]) -> str:
    """Serialize a C++ body node to a normalized token string."""
    mapping: dict[str, str] = {}
    tokens: list[str] = []

    def visit(n: Node) -> None:
        if n.type == "comment":
            return
        if not n.children:
            tokens.append(_cpp_leaf_token(n, locals_, mapping))
            return
        if n.type in _CPP_STRING_NODE_TYPES:
            tokens.append("_S_")
            return
        for c in n.children:
            visit(c)

    visit(body)
    return " ".join(tokens)


def _cpp_leaf_token(n: Node, locals_: set[str], mapping: dict[str, str]) -> str:
    """The normalized token for a C++ leaf node."""
    t = n.type
    raw = _node_text(n)
    if t == "identifier" and raw in locals_:
        if raw not in mapping:
            mapping[raw] = f"_v{len(mapping)}"
        return mapping[raw]
    if t in _CPP_STRING_LEAF_TYPES:
        return "_S_"
    if t == "number_literal":
        return "_N_"
    return raw


def _enclosing_class_cpp(func_node: Node) -> str | None:
    """Return the enclosing class/struct name for a C++ function, or None."""
    parent = func_node.parent
    while parent is not None:
        if parent.type == "field_declaration_list":
            grandparent = parent.parent
            if grandparent is not None and grandparent.type in (
                "class_specifier",
                "struct_specifier",
            ):
                name_node = _child(grandparent, "name")
                if name_node:
                    return _node_text(name_node)
        parent = parent.parent
    return None


def _cpp_func_name(n: Node) -> str:
    """Best-effort function name from a C++ function_definition declarator."""
    decl = _child(n, "declarator")
    if decl is None:
        return "<unknown>"
    inner = decl
    while inner.type in ("pointer_declarator", "reference_declarator"):
        inner = inner.child_by_field_name("declarator") or inner
        if inner == decl:
            break
        decl = inner
    if inner.type == "function_declarator":
        name_node = inner.child_by_field_name("declarator")
        return _node_text(name_node) if name_node else _node_text(inner)
    return _node_text(inner)


def _iter_functions_cpp(root_node: Node) -> Iterator[tuple[Node, str]]:
    """Yield `(func_node, symbol)` for every C++ function_definition."""
    if root_node.type == "function_definition":
        body = _child(root_node, "body")
        if body is not None:
            func_name = _cpp_func_name(root_node)
            class_name = _enclosing_class_cpp(root_node)
            symbol = f"{class_name}.{func_name}" if class_name else func_name
            yield root_node, symbol
    for c in root_node.named_children:
        yield from _iter_functions_cpp(c)

"""C++ fingerprinting + function iteration for the legacy dup scan.

Mirrors `_legacy_py` for the tree-sitter C++ grammar: declarator-name
harvesting for locals, body serialization, and a function-node walker.
"""

from __future__ import annotations

from collections.abc import Iterator

from tree_sitter import Node

from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text


def _collect_locals_cpp(func_node: Node) -> set[str]:
    """Collect identifiers local to a C++ function (params + declarations).

    T-1509: tree-sitter's cpp grammar puts the `parameters` field on the
    `function_declarator` node (`func_node`'s `declarator` field), not on
    `function_definition` itself -- `_child(func_node, "parameters")`
    always returned `None`, so no C++ function's parameters were ever
    added as locals here. `_cpp_function_declarator` walks through any
    pointer/reference declarator wrapping (mirroring `_cpp_func_name`'s
    own unwrap) to reach the real `function_declarator` first.
    """
    locals_: set[str] = set()
    declarator = _child(func_node, "declarator")
    func_declarator = _cpp_function_declarator(declarator) if declarator else None
    params = _child(func_declarator, "parameters") if func_declarator else None
    if params:
        for c in params.named_children:
            _harvest_cpp_param(c, locals_)
    body = _child(func_node, "body")
    if body:
        _collect_assigned_names_cpp(body, locals_)
    return locals_


def _cpp_function_declarator(node: Node) -> Node | None:
    """Unwrap pointer/reference declarator wrapping to the inner
    `function_declarator` node carrying the `parameters` field, or `None`
    if `node` is not (and does not wrap) one."""
    while node.type in ("pointer_declarator", "reference_declarator"):
        inner = node.child_by_field_name("declarator")
        if inner is None:
            return None
        # frob:invariant terminates reason="inner is node's own 'declarator' field child, a proper descendant in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
        node = inner
    return node if node.type == "function_declarator" else None


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
    """Unwrap pointer/reference declarators to the identifier name(s) inside.

    T-1509: `reference_declarator` (`int& c`) does not label its inner
    identifier with a `declarator` field the way `pointer_declarator`
    (`int* b`) does in this tree-sitter-cpp grammar version -- verified
    directly, `child_by_field_name("declarator")` returns `None` for a
    real `reference_declarator` node. Falling back to `named_children`
    when the field lookup misses covers this without a grammar-version
    special case: it is a no-op for `pointer_declarator` (whose field
    lookup already succeeds) and correctly reaches the bare `identifier`
    child for `reference_declarator`.
    """
    if node.type == "identifier":
        out.add(_node_text(node))
    elif node.type in (
        "pointer_declarator",
        "reference_declarator",
        "abstract_pointer_declarator",
    ):
        inner = node.child_by_field_name("declarator")
        if inner is not None:
            # frob:invariant terminates reason="inner is node's own 'declarator' field child, a proper descendant in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
            _harvest_cpp_declarator_name(inner, out)
        else:
            for c in node.named_children:
                # frob:invariant terminates reason="c ranges over node's named_children, each a proper descendant in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
                _harvest_cpp_declarator_name(c, out)
    else:
        for c in node.named_children:
            # frob:invariant terminates reason="c ranges over node's named_children, each a proper descendant in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
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
            # frob:invariant terminates reason="c ranges over node's named_children, each a proper descendant in the finite tree-sitter parse tree; mutually recurses with _harvest_cpp_for below, which also only descends into init/body children" measure="node's subtree depth strictly decreases"  # noqa: E501
            _collect_assigned_names_cpp(c, out)


def _harvest_cpp_for(node: Node, out: set[str]) -> None:
    """Harvest binding names from a C++ for-loop's initializer and body."""
    init = node.child_by_field_name("initializer")
    if init:
        # frob:invariant terminates reason="init is node's own 'initializer' field child, a proper descendant in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
        _collect_assigned_names_cpp(init, out)
    body = node.child_by_field_name("body")
    if body:
        # frob:invariant terminates reason="body is node's own 'body' field child, a proper descendant in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
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
        # frob:invariant terminates reason="c ranges over root_node's named_children, each a proper descendant in the finite tree-sitter parse tree" measure="root_node's subtree depth strictly decreases"  # noqa: E501
        yield from _iter_functions_cpp(c)

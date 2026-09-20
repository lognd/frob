"""C# fingerprinting + function iteration for the legacy dup scan (T-4510).

Mirrors `_legacy_py.py` for the tree-sitter C# grammar (tree-sitter-c-sharp,
real named fields verified interactively against a parsed sample --
`method_declaration`'s own `name`/`parameters`/`body`, `parameter`'s
`name`, `variable_declarator`'s `name`, `for_statement`'s `initializer`/
`body`): deliberately narrower than the python/C++ walkers -- it
recognizes the local-binding shapes that actually appear in idiomatic C#
method bodies (parameters, `var x = ...`/typed local declarations,
`for`/`foreach` loop variables) rather than exhaustively covering every
binding form the grammar can produce. A binding shape it does not
recognize is simply never added to `locals_`, which only narrows Type-2
(renamed) matching for a fragment using that shape -- Type-1 (exact)
matching, which does not consult `locals_` at all, is unaffected.

T-4510's own finding: before this module existed, `frob.dup._legacy.
_scan_tree` dispatched only on `_PY_EXTS`/`_CPP_EXTS`, so `.cs` files were
never scanned at all despite `csharp` being a real `LANGUAGES` entry in
`frob.dup._exhaustiveness` and a real `_CSHARP_LANGS`-routed facet in
`frob.lang._support` -- the dup facet's "implemented" claim for csharp
was unproven until this module and `_legacy._scan_cs_file`/`_CS_EXTS`
closed the gap.
"""

from __future__ import annotations

from collections.abc import Iterator

from tree_sitter import Node

from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text


# frob:ticket T-4543
# frob:waive WIRE001 follow_up="T-4950" reason="passed as a callable argument to _index_function in _legacy.py._scan_cs_file (same indirect-call shape as the pre-existing _collect_locals_cpp/_collect_locals_py siblings, which WIRE001 does not flag only because they are not new in this diff)"  # noqa: E501
def _collect_locals_cs(func_node: Node) -> set[str]:
    """Collect identifiers local to a C# method (params + declarations)."""
    locals_: set[str] = set()
    params = _child(func_node, "parameters")
    if params:
        for c in params.named_children:
            _harvest_cs_param(c, locals_)
    body = _child(func_node, "body")
    if body:
        _collect_assigned_names_cs(body, locals_)
    return locals_


# frob:ticket T-4543
def _harvest_cs_param(node: Node, out: set[str]) -> None:
    """Add the bound name of one C# `parameter` node to `out`."""
    if node.type == "parameter":
        name_node = node.child_by_field_name("name")
        if name_node:
            out.add(_node_text(name_node))


# frob:ticket T-4543
def _harvest_cs_declarator(node: Node, out: set[str]) -> None:
    """Add the bound name of one `variable_declarator` node to `out`."""
    if node.type != "variable_declarator":
        return
    name_node = node.child_by_field_name("name")
    if name_node is not None:
        out.add(_node_text(name_node))
        return
    for c in node.named_children:
        if c.type == "identifier":
            out.add(_node_text(c))
            return


# frob:ticket T-4543
def _harvest_cs_variable_declaration(node: Node, out: set[str]) -> None:
    """Add every declarator name under one `variable_declaration` node."""
    for declarator in node.named_children:
        _harvest_cs_declarator(declarator, out)


# frob:ticket T-4543
def _collect_assigned_names_cs(node: Node, out: set[str]) -> None:
    """Walk a C# method body and harvest local-declaration/loop binding
    names (parameters are collected separately by `_collect_locals_cs`)."""
    for c in node.named_children:
        t = c.type
        if t == "local_declaration_statement":
            for var_decl in c.named_children:
                if var_decl.type == "variable_declaration":
                    _harvest_cs_variable_declaration(var_decl, out)
        elif t == "for_statement":
            init = c.child_by_field_name("initializer")
            if init is not None and init.type == "variable_declaration":
                _harvest_cs_variable_declaration(init, out)
            body = c.child_by_field_name("body")
            if body:
                # frob:invariant terminates reason="body is c's own 'body' field child, a proper descendant in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
                _collect_assigned_names_cs(body, out)
        elif t in ("foreach_statement",):
            left = c.child_by_field_name("left")
            if left is not None and left.type == "identifier":
                out.add(_node_text(left))
            body = c.child_by_field_name("body")
            if body:
                # frob:invariant terminates reason="body is c's own 'body' field child, a proper descendant in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
                _collect_assigned_names_cs(body, out)
        elif t in (
            "if_statement",
            "while_statement",
            "do_statement",
            "block",
            "try_statement",
        ):
            # frob:invariant terminates reason="c is a proper descendant of node in the finite tree-sitter parse tree" measure="node's subtree depth strictly decreases"  # noqa: E501
            _collect_assigned_names_cs(c, out)


# frob:ticket T-4543
_CS_LITERAL_COLLAPSE_TYPES = frozenset(
    {
        "string_literal",
        "verbatim_string_literal",
        "interpolated_string_expression",
        "character_literal",
        "raw_string_literal",
    }
)


# frob:ticket T-4543
# frob:waive WIRE001 follow_up="T-4950" reason="passed as a callable argument to _index_function in _legacy.py._scan_cs_file (same indirect-call shape as the pre-existing _serialize_cpp_body/_serialize_py_body siblings, which WIRE001 does not flag only because they are not new in this diff)"  # noqa: E501
def _serialize_cs_body(body: Node, locals_: set[str]) -> str:
    """Serialize a C# body node to a normalized token string."""
    mapping: dict[str, str] = {}
    tokens: list[str] = []

    def visit(n: Node) -> None:
        if n.type == "comment":
            return
        if n.type in _CS_LITERAL_COLLAPSE_TYPES:
            tokens.append("_S_")
            return
        if not n.children:
            tokens.append(_cs_leaf_token(n, locals_, mapping))
            return
        for c in n.children:
            visit(c)

    visit(body)
    return " ".join(tokens)


# frob:ticket T-4543
def _cs_leaf_token(n: Node, locals_: set[str], mapping: dict[str, str]) -> str:
    """The normalized token for a C# leaf node: renamed local, `_N_`
    numeric-literal placeholder, or the raw text."""
    t = n.type
    raw = _node_text(n)
    if t == "identifier" and raw in locals_:
        if raw not in mapping:
            mapping[raw] = f"_v{len(mapping)}"
        return mapping[raw]
    if t in ("integer_literal", "real_literal"):
        return "_N_"
    return raw


# frob:ticket T-4543
def _enclosing_class_cs(func_node: Node) -> str | None:
    """Return the enclosing class/struct/interface name for a C# method,
    or None."""
    parent = func_node.parent
    while parent is not None:
        if parent.type == "declaration_list":
            grandparent = parent.parent
            if grandparent is not None and grandparent.type in (
                "class_declaration",
                "struct_declaration",
                "interface_declaration",
            ):
                name_node = grandparent.child_by_field_name("name")
                if name_node:
                    return _node_text(name_node)
        parent = parent.parent
    return None


# frob:ticket T-4543
def _cs_func_name(node: Node) -> str:
    """Best-effort method name from a C# `method_declaration` node."""
    name_node = node.child_by_field_name("name")
    return _node_text(name_node) if name_node else "<unknown>"


# frob:ticket T-4543
def _iter_functions_cs(root_node: Node) -> Iterator[tuple[Node, str]]:
    """Yield `(func_node, symbol)` for every C# `method_declaration`."""
    if root_node.type == "method_declaration":
        body = _child(root_node, "body")
        if body is not None:
            func_name = _cs_func_name(root_node)
            class_name = _enclosing_class_cs(root_node)
            symbol = f"{class_name}.{func_name}" if class_name else func_name
            yield root_node, symbol
    for c in root_node.named_children:
        # frob:invariant terminates reason="c ranges over root_node's named_children, each a proper descendant in the finite tree-sitter parse tree" measure="root_node's subtree depth strictly decreases"  # noqa: E501
        yield from _iter_functions_cs(c)

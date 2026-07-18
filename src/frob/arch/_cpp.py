"""C++ architectural checks: long-function and god-class (docs/modules/arch.md).

Best-effort structural checks over the tree-sitter C++ grammar; the smaller
rule surface than Python (no coupling/nesting/abstraction) mirrors the
grammar's lack of a single import mechanism to reason about.
"""

from __future__ import annotations

from typing import cast

from tree_sitter import Tree

from frob.arch._models import ArchSuggestion
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text


def _check_long_functions(
    tree: object,
    rel: str,
    max_function_lines: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag C++ function definitions whose body exceeds `max_function_lines`."""
    from frob.lang import cpp_function_nodes

    t: Tree = cast("Tree", tree)
    for node, name in cpp_function_nodes(t):
        if node.type != "function_definition":
            continue
        body = _child(node, "body")
        if body is None:
            continue
        n_lines = body.end_point[0] - body.start_point[0] + 1
        if n_lines <= max_function_lines:
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=node.start_point[0] + 1,
                category="long-function",
                severity="warning",
                message=f"function `{name}` has {n_lines} lines"
                f" (threshold: {max_function_lines})",
            )
        )


def _check_god_classes(
    tree: object,
    rel: str,
    max_class_methods: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag C++ classes/structs with more than `max_class_methods` members."""
    t: Tree = cast("Tree", tree)
    for c in t.root_node.named_children:
        if c.type not in ("class_specifier", "struct_specifier"):
            continue
        body = _child(c, "body")
        if body is None:
            continue
        methods = [
            n
            for n in body.named_children
            if n.type in ("function_definition", "declaration")
        ]
        n_methods = len(methods)
        if n_methods <= max_class_methods:
            continue
        name_node = _child(c, "name")
        cname = _node_text(name_node) if name_node else "?"
        out.append(
            ArchSuggestion(
                file=rel,
                line=c.start_point[0] + 1,
                category="god-class",
                severity="warning",
                message=f"class `{cname}` has {n_methods} methods"
                f" (threshold: {max_class_methods})",
            )
        )

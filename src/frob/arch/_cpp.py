"""C++ architectural checks: long-function and god-class (docs/modules/arch.md).

Best-effort structural checks over the tree-sitter C++ grammar; the smaller
rule surface than Python (no coupling/nesting/abstraction) mirrors the
grammar's lack of a single import mechanism to reason about.
"""

# frob:waive TEST005 reason="module line coverage 23.5%, debt T-0160"

from __future__ import annotations

from typing import cast

from tree_sitter import Node, Tree

from frob.arch._models import ArchSuggestion
from frob.lang import child_by_field as _child
from frob.lang import node_text as _node_text

# T-0289: parity with `frob.arch._python`'s complexity-aware long-function
# rule -- see that module's `_BRANCH_NODE_TYPES` comment for the full
# rationale. `switch_statement`/`case_statement` are deliberately excluded
# for the same reason python's `match_statement`/`case_clause` are: a
# switch/case is flat dispatch, not the decision complexity this rule
# targets.
_NESTING_TYPES = frozenset(
    {"if_statement", "for_statement", "while_statement", "try_statement"}
)
_BRANCH_NODE_TYPES = frozenset(
    {
        "if_statement",
        "for_statement",
        "while_statement",
        "catch_clause",
        "conditional_expression",
    }
)
_LONG_FUNCTION_NESTING_THRESHOLD = 3
_LONG_FUNCTION_CYCLOMATIC_THRESHOLD = 8


def _cpp_max_nesting(node: Node) -> int:
    """Deepest control-flow nesting depth inside a C++ function body (T-0289)."""

    def depth(n: Node, current: int) -> int:
        best = current
        for c in n.children:
            nxt = current + 1 if c.type in _NESTING_TYPES else current
            best = max(best, depth(c, nxt))
        return best

    return depth(node, 0)


def _cpp_cyclomatic(node: Node) -> int:
    """Cheap cyclomatic-complexity proxy for a C++ function body (T-0289);
    also counts `&&`/`||` inside `binary_expression` nodes as decision
    points, mirroring python's `boolean_operator`."""
    count = 1 if node.type in _BRANCH_NODE_TYPES else 0
    if node.type == "binary_expression" and any(
        c.type in ("&&", "||") for c in node.children
    ):
        count += 1
    for c in node.children:
        count += _cpp_cyclomatic(c)
    return count


def _cpp_is_complex(body: Node) -> bool:
    """Whether a C++ function body is structurally complex enough for the
    long-function rule to fire (T-0289) -- parity with `_python._py_is_complex`."""
    return (
        _cpp_max_nesting(body) >= _LONG_FUNCTION_NESTING_THRESHOLD
        or _cpp_cyclomatic(body) >= _LONG_FUNCTION_CYCLOMATIC_THRESHOLD
    )


def _check_long_functions(
    tree: object,
    rel: str,
    max_function_lines: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag C++ function definitions that are BOTH longer than
    `max_function_lines` AND structurally complex (`_cpp_is_complex`, T-0289)."""
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
        if not _cpp_is_complex(body):
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=node.start_point[0] + 1,
                category="long-function",
                severity="warning",
                message=f"function `{name}` has {n_lines} lines"
                f" (threshold: {max_function_lines})",
                symref=f"{rel}::{name}",
                metric=n_lines,
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

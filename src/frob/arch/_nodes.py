"""Tiny tree-sitter node conveniences shared by the arch language walkers.

`_child`/`_node_text` are trivial `child_by_field_name`/decode one-liners
kept in one home so every per-language walker (`_python`, `_cpp`) shares
them rather than repeating the field-lookup/decode dance.
"""

from __future__ import annotations

from tree_sitter import Node


def _child(node: Node, field: str) -> Node | None:
    """`node.child_by_field_name(field)` -- a one-line convenience so every
    walker doesn't repeat the tree-sitter field-lookup call directly."""
    return node.child_by_field_name(field)


def _node_text(node: Node | None) -> str:
    """Decode `node`'s own text, or '' if absent (missing name = grammar bug)."""
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8", errors="replace")

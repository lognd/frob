"""Shared node/hash helpers for the legacy Type-1/Type-2 dup scan.

`_child`/`_node_text` are trivial `child_by_field_name`/decode one-liners;
`_sha16` is the 16-hex-char body digest both language scanners key on.
"""

from __future__ import annotations

import hashlib

from tree_sitter import Node


def _child(node: Node, field: str) -> Node | None:
    """`node.child_by_field_name(field)` -- see the legacy module docstring."""
    return node.child_by_field_name(field)


def _node_text(node: Node | None) -> str:
    """Decode `node`'s own text, or '' if absent (missing name = grammar bug)."""
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8", errors="replace")


def _sha16(s: str) -> str:
    """First 16 hex chars of sha256(s) -- the fragment/body fingerprint."""
    return hashlib.sha256(s.encode()).hexdigest()[:16]

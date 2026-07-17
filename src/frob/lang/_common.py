"""Shared, language-agnostic tree-sitter helpers (the walker skeleton).

Every grammar tree-sitter hands back is formatting-insensitive at the leaf
level: whitespace is never itself a node. That single property is what lets
``leaf_tokens`` double as the entire "normalized token" story for the sig/
body digest contract in docs/graph.md -- no per-language pretty-printer is
needed, only a byte-range exclusion list (a symbol's own body, a docstring
statement) and a comment-type-name set. Keeping that trick here, instead of
re-deriving it in each of the five per-language walkers in ``_extract.py``,
is what keeps this package free of the five-way duplication the task spec
explicitly forbids.
"""

from __future__ import annotations

from tree_sitter import Node

ByteRange = tuple[int, int]


def collapse_ws(text: str) -> str:
    """Whitespace-collapse doc text so reflow never changes ``doc_text``."""
    return " ".join(text.split())


def _in_skip_range(node: Node, skip_ranges: tuple[ByteRange, ...]) -> bool:
    """True if `node`'s byte span is fully covered by one skip range."""
    for start, end in skip_ranges:
        if node.start_byte >= start and node.end_byte <= end:
            return True
    return False


def leaf_tokens(
    node: Node,
    comment_types: frozenset[str],
    skip_ranges: tuple[ByteRange, ...] = (),
) -> tuple[str, ...]:
    """Collect leaf-node text under `node`, skipping comments and exclusions.

    Leaves are tree-sitter tokens with no children -- whitespace is never
    represented as a node, so this sequence is stable across reformatting
    and only changes when a real token (identifier, keyword, literal,
    punctuation) is added, removed, or renamed.
    """
    tokens: list[str] = []

    def walk(n: Node) -> None:
        if _in_skip_range(n, skip_ranges):
            return
        if n.child_count == 0:
            if n.type in comment_types:
                return
            text = n.text
            if text is not None:
                tokens.append(text.decode("utf-8", errors="replace"))
            return
        for child in n.children:
            walk(child)

    walk(node)
    return tuple(tokens)


def strip_comment_delims(raw: str) -> str:
    """Strip `//`, `///`, `/* */`, `/** */`, and leading `*` from one comment."""
    text = raw.strip()
    if text.startswith("/**"):
        text = text[3:]
        if text.endswith("*/"):
            text = text[:-2]
    elif text.startswith("/*"):
        text = text[2:]
        if text.endswith("*/"):
            text = text[:-2]
    elif text.startswith("///"):
        text = text[3:]
    elif text.startswith("//"):
        text = text[2:]
    elif text.startswith("#"):
        text = text[1:]
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("*"):
            stripped = stripped[1:]
        lines.append(stripped)
    return " ".join(lines)


def leading_doc_comment(
    node: Node,
    comment_types: frozenset[str],
) -> str:
    """Gather the contiguous comment block directly above `node` as doc text.

    Contiguous means each comment sibling ends on the line immediately
    before the next token starts -- a blank line breaks the chain, matching
    the "immediately above" rule in the token contract.
    """
    parent = node.parent
    if parent is None:
        return ""
    siblings = parent.children
    idx = siblings.index(node)
    collected: list[str] = []
    expected_end_row = node.start_point[0]
    i = idx - 1
    while i >= 0:
        sib = siblings[i]
        if sib.type not in comment_types:
            break
        if sib.end_point[0] + 1 < expected_end_row:
            break
        collected.append(strip_comment_delims(child_text(sib)))
        expected_end_row = sib.start_point[0]
        i -= 1
    collected.reverse()
    return collapse_ws(" ".join(collected))


def span_of(node: Node) -> tuple[int, int]:
    """1-based inclusive (start_line, end_line) span for `node`.

    Some tokens (e.g. a rust `///` line comment whose text includes the
    trailing newline) report an `end_point` at column 0 of the following
    line -- that is a lexer artifact, not real content on that line, so it
    is folded back onto the line the content actually occupies.
    """
    end_row = node.end_point[0]
    if node.end_point[1] == 0 and end_row > node.start_point[0]:
        end_row -= 1
    return (node.start_point[0] + 1, end_row + 1)


def child_text(node: Node | None) -> str:
    """Decode a node's own text, or '' if the node is absent -- a programmer
    convenience for optional field lookups (missing name is a grammar bug,
    not a runtime error worth a Result)."""
    if node is None or node.text is None:
        return ""
    return node.text.decode("utf-8", errors="replace")

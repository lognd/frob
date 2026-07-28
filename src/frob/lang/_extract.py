"""Extraction dispatch: symbols, comments, imports, and identifiers
(docs/modules/lang.md).

Five grammars, five node vocabularies -- python's docstring-as-first-
statement has no analogue in rust's `///`-comment-above-item convention, and
C's file-scope-`static` publicness rule has no analogue in TypeScript's
`export` keyword. Those per-language differences live in one small walker
module each (`_walk_python`, `_walk_typescript`, `_walk_rust`, `_walk_c`).
This module owns only what is genuinely language-agnostic: the symbol-walker
dispatch table, comment extraction and its enclosing/following binding, and
the narrower import/identifier walks `frob.cycle` and `frob.xref` consume.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/lang/_extract.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from tree_sitter import Node, Tree

from frob.lang._common import _child_text, _span_of, _strip_comment_delims
from frob.lang._common import _find_enclosing_symbol as _find_enclosing
from frob.lang._common import _find_following_symbol as _find_following
from frob.lang._models import RawComment, RawSymbol
from frob.lang._walk_c import _walk_c_family
from frob.lang._walk_kotlin import _walk_kotlin
from frob.lang._walk_python import _walk_python, _walk_python_docstring_comments
from frob.lang._walk_rust import _walk_rust
from frob.lang._walk_typescript import _walk_typescript
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/lang.md#comment-extraction-and-binding
COMMENT_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"comment"}),
    "typescript": frozenset({"comment"}),
    "tsx": frozenset({"comment"}),
    "rust": frozenset({"line_comment", "block_comment"}),
    "c": frozenset({"comment"}),
    "cpp": frozenset({"comment"}),
    "kotlin": frozenset({"line_comment", "multiline_comment"}),
}


def _walk_c(root: Node) -> tuple[RawSymbol, ...]:
    """C symbol walk (C comment-node types)."""
    return _walk_c_family(root, COMMENT_TYPES["c"])


def _walk_cpp(root: Node) -> tuple[RawSymbol, ...]:
    """C++ symbol walk (C++ comment-node types)."""
    return _walk_c_family(root, COMMENT_TYPES["cpp"])


def _walk_tsx(root: Node) -> tuple[RawSymbol, ...]:
    """TSX symbol walk (identical to TypeScript)."""
    return _walk_typescript(root)


_WALKERS = {
    "python": _walk_python,
    "typescript": _walk_typescript,
    "tsx": _walk_tsx,
    "rust": _walk_rust,
    "c": _walk_c,
    "cpp": _walk_cpp,
    "kotlin": _walk_kotlin,
}

# frob:ticket T-0342
# Per-language docstring-directive scan, additive to `COMMENT_TYPES`'
# comment-node walk: python's docstring-as-first-statement convention has
# no `comment`-typed node at all, so a `frob:` directive written inside one
# is invisible unless a language also gets its own docstring walk here.
# Only python has one today; the ticket's body notes the same gap likely
# exists for other languages' doc-comment conventions but leaves that for
# a follow-up (out of this ticket's repro/scope).
_DOCSTRING_COMMENT_WALKERS = {
    "python": _walk_python_docstring_comments,
}


# frob:doc docs/modules/lang.md#extraction-api
# frob:doc docs/guides/extending/language-grammar-handlers.md#language-grammar-handlers
def extract(
    tree: Tree, source: bytes, language: str
) -> tuple[tuple[RawSymbol, ...], tuple[RawComment, ...]]:
    """Extract symbols then comments (order matters: comments bind to symbol spans)."""
    walker = _WALKERS[language]
    symbols = walker(tree.root_node)
    comments = _extract_comments(tree.root_node, COMMENT_TYPES[language], symbols)
    docstring_walker = _DOCSTRING_COMMENT_WALKERS.get(language)
    if docstring_walker is not None:
        comments = comments + docstring_walker(tree.root_node, symbols)
    _log.debug(
        "extracted %d symbols, %d comments for language=%s",
        len(symbols),
        len(comments),
        language,
    )
    return symbols, comments


def _extract_comments(
    root: Node,
    comment_types: frozenset[str],
    symbols: tuple[RawSymbol, ...],
) -> tuple[RawComment, ...]:
    """Walk the whole tree for comment-typed leaves, then bind enclosing/following.

    Adjacent comment lines (no blank line between them) are one contiguous
    block: every comment in the block resolves `following` against the
    block's *last* line, not its own line (T-0100). Without this, a stack of
    3+ directive comments above a def silently loses the topmost ones -- the
    fixed 2-line lookahead from each comment's own end can no longer reach
    the def once enough comments pile up in front of it.
    """
    raw_nodes = _collect_comment_nodes(root, comment_types)
    block_end = _block_ends(raw_nodes)
    return _bind_comments(raw_nodes, block_end, symbols)


def _collect_comment_nodes(root: Node, comment_types: frozenset[str]) -> list[Node]:
    """Depth-first collect comment-typed leaves under `root`, sorted by
    start line."""
    raw_nodes: list[Node] = []

    def walk(n: Node) -> None:
        if n.type in comment_types:
            raw_nodes.append(n)
            return
        for child in n.children:
            walk(child)

    walk(root)
    # frob:waive PERF004 reason="one sort per file, not in a loop; walk() is recursion"
    raw_nodes.sort(key=lambda n: _span_of(n)[0])
    return raw_nodes


def _bind_comments(
    raw_nodes: list[Node],
    block_end: list[int],
    symbols: tuple[RawSymbol, ...],
) -> tuple[RawComment, ...]:
    """Pair each comment node with its block end line and resolve its
    enclosing/following symbol bindings."""
    out: list[RawComment] = []
    for node, end in zip(raw_nodes, block_end, strict=True):
        span = _span_of(node)
        text = _strip_comment_delims(_child_text(node))
        enclosing = _find_enclosing(span, symbols)
        following = _find_following((span[0], end), symbols)
        out.append(
            RawComment(text=text, span=span, enclosing=enclosing, following=following)
        )
    return tuple(out)


def _effective_end_row(node: Node) -> int:
    """0-based end row `node` actually occupies, with the tree-sitter
    trailing-newline artifact folded back (the same rule `_span_of` applies,
    T-0301): some comment nodes -- a rust `///` line comment is the
    reproducing case -- report `end_point` at column 0 of the FOLLOWING
    line rather than ending on their own row. Comparing raw `end_point[0]`
    values (as `_is_trailing_comment` used to) treats every doc-comment
    line whose predecessor is ALSO a doc-comment line as "trailing" (the
    artifact makes the predecessor's raw end row equal this node's start
    row), which silently truncated `_block_ends`'s backward chain after the
    first line of any 3+-line `///` block -- exactly the escalation this
    fixes (a `// frob:doc` placed above a multi-line rustdoc block failing
    to bind; single-line rustdoc happened to have only one such comparison
    and so looked fine). Reuses `_span_of`'s own fold rule (1-based inclusive
    end line) rather than re-deriving it, so the artifact-correction logic
    lives in exactly one place."""
    return _span_of(node)[1] - 1


def _is_trailing_comment(node: Node) -> bool:
    """True when `node` shares its source line with code (a trailing `# ...`).

    A trailing comment -- `def foo():  # noqa: N802` -- is not a standalone
    directive line: it starts after real code on the same row, so its own
    line is really the *code's* line, not a comment line. Detected via the
    node's previous tree sibling ending on the same row (T-0100): a
    standalone comment's previous sibling, if any, ends on an earlier row.
    Both sides are compared via `_effective_end_row`/`start_point`, never
    raw `end_point` (T-0301) -- see `_effective_end_row` for why a raw
    comparison misfires whenever the previous sibling is itself a
    doc-comment line.
    """
    prev = node.prev_sibling
    return prev is not None and _effective_end_row(prev) == node.start_point[0]


def _block_ends(sorted_nodes: list[Node]) -> list[int]:
    """Last line of each node's contiguous (no-blank-line-gap) comment run.

    Walked back-to-front so every comment in a stacked block inherits the
    end line of the block's last member, letting `_find_following`'s window
    reach the def below the whole block rather than just the nearest line.

    A trailing comment (T-0100) never joins a block, in either direction: it
    cannot be chained *into* (its own line already holds code -- often the
    very def a directive above it is trying to bind to, so absorbing it
    would push the following-window past the def) and, symmetrically, it
    never extends a block backward through itself since it is excluded as a
    valid chain target below.
    """
    ends = [_span_of(n)[1] for n in sorted_nodes]
    starts = [_span_of(n)[0] for n in sorted_nodes]
    trailing = [_is_trailing_comment(n) for n in sorted_nodes]
    block_end = [0] * len(sorted_nodes)
    for i in range(len(sorted_nodes) - 1, -1, -1):
        chains_forward = (
            i != len(sorted_nodes) - 1
            and starts[i + 1] == ends[i] + 1
            and not trailing[i + 1]
        )
        block_end[i] = block_end[i + 1] if chains_forward else ends[i]
    return block_end


# ------------------------------------------------------------------ imports
#
# frob.cycle needs raw import/include specifiers (unresolved -- "os.path",
# "local.h") to build its dependency graph; this is a second, narrower walk
# per language, kept here next to the symbol walkers so cycle detection
# never has to touch tree-sitter nodes directly (docs/modules/lang.md).


def _python_import_specifiers(n: Node) -> list[str]:
    """Import specifiers declared by one python `import`/`from` statement node."""
    if n.type == "import_statement":
        return [_child_text(child) for child in n.named_children]
    if n.type == "import_from_statement":
        mod = n.child_by_field_name("module_name")
        return [_child_text(mod)] if mod is not None else []
    return []


def _imports_python(root: Node) -> tuple[str, ...]:
    results: list[str] = []

    def visit(n: Node) -> None:
        results.extend(_python_import_specifiers(n))
        for child in n.children:
            visit(child)

    visit(root)
    return tuple(results)


def _imports_c_family(root: Node) -> tuple[str, ...]:
    """Every `#include`, quoted (local) or angled (system) alike.

    Local-vs-system is not this walker's call -- `resolve_local_import`
    naturally drops system includes (they never resolve to a file under the
    scan root), and callers that just want to *display* every include (the
    outline command) need both.
    """
    results: list[str] = []

    def visit(n: Node) -> None:
        if n.type == "preproc_include":
            path_node = n.named_children[0] if n.named_children else None
            if path_node is not None:
                results.append(_child_text(path_node).strip('"<>'))
        for child in n.children:
            visit(child)

    visit(root)
    return tuple(results)


_IMPORT_WALKERS = {
    "python": _imports_python,
    "c": _imports_c_family,
    "cpp": _imports_c_family,
}


# frob:doc docs/modules/lang.md#extraction-api
# frob:waive TEST005 reason="extract_imports 80.0% branch cover, debt T-0160"
def extract_imports(tree: Tree, language: str) -> tuple[str, ...]:
    """Raw import/include specifiers for `language` (empty tuple if unsupported)."""
    walker = _IMPORT_WALKERS.get(language)
    if walker is None:
        return ()
    return walker(tree.root_node)


# --------------------------------------------------------------- identifiers
#
# frob.xref needs every identifier-token occurrence (name, line) to find
# usages, not just declarations -- a different shape than RawSymbol, so it
# gets its own narrow walk rather than forcing xref to reach into tree-sitter.

_IDENTIFIER_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"identifier"}),
    "c": frozenset({"identifier", "type_identifier"}),
    "cpp": frozenset({"identifier", "type_identifier"}),
}


# frob:doc docs/modules/lang.md#extraction-api
def iter_identifiers(tree: Tree, language: str) -> tuple[tuple[str, int], ...]:
    """(name, 1-based line) for every identifier-like leaf (empty if unsupported)."""
    types = _IDENTIFIER_TYPES.get(language)
    if types is None:
        return ()
    out: list[tuple[str, int]] = []

    def visit(n: Node) -> None:
        if n.type in types:
            txt = _child_text(n)
            if txt:
                out.append((txt, _span_of(n)[0]))
            return
        for child in n.children:
            visit(child)

    visit(tree.root_node)
    return tuple(out)

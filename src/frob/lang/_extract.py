"""Extraction dispatch: symbols, comments, imports, and identifiers (docs/lang.md).

Five grammars, five node vocabularies -- python's docstring-as-first-
statement has no analogue in rust's `///`-comment-above-item convention, and
C's file-scope-`static` publicness rule has no analogue in TypeScript's
`export` keyword. Those per-language differences live in one small walker
module each (`_walk_python`, `_walk_typescript`, `_walk_rust`, `_walk_c`).
This module owns only what is genuinely language-agnostic: the symbol-walker
dispatch table, comment extraction and its enclosing/following binding, and
the narrower import/identifier walks `frob.cycle` and `frob.xref` consume.
"""

from __future__ import annotations

from tree_sitter import Node, Tree

from frob.lang._common import child_text, span_of, strip_comment_delims
from frob.lang._models import RawComment, RawSymbol
from frob.lang._walk_c import _walk_c_family
from frob.lang._walk_python import _walk_python
from frob.lang._walk_rust import _walk_rust
from frob.lang._walk_typescript import _walk_typescript
from frob.logging import get_logger

_log = get_logger(__name__)


COMMENT_TYPES: dict[str, frozenset[str]] = {
    "python": frozenset({"comment"}),
    "typescript": frozenset({"comment"}),
    "tsx": frozenset({"comment"}),
    "rust": frozenset({"line_comment", "block_comment"}),
    "c": frozenset({"comment"}),
    "cpp": frozenset({"comment"}),
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
}


# frob:doc docs/lang.md#extraction-api
def extract(
    tree: Tree, source: bytes, language: str
) -> tuple[tuple[RawSymbol, ...], tuple[RawComment, ...]]:
    """Extract symbols then comments (order matters: comments bind to symbol spans)."""
    walker = _WALKERS[language]
    symbols = walker(tree.root_node)
    comments = _extract_comments(tree.root_node, COMMENT_TYPES[language], symbols)
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
    """Walk the whole tree for comment-typed leaves, then bind enclosing/following."""
    raw_nodes: list[Node] = []

    def walk(n: Node) -> None:
        if n.type in comment_types:
            raw_nodes.append(n)
            return
        for child in n.children:
            walk(child)

    walk(root)

    out: list[RawComment] = []
    for node in raw_nodes:
        span = span_of(node)
        text = strip_comment_delims(child_text(node))
        enclosing = _find_enclosing(span, symbols)
        following = _find_following(span, symbols)
        out.append(
            RawComment(text=text, span=span, enclosing=enclosing, following=following)
        )
    return tuple(out)


def _find_enclosing(
    span: tuple[int, int], symbols: tuple[RawSymbol, ...]
) -> str | None:
    """Deepest (narrowest-span) symbol whose span fully contains `span`."""
    best: RawSymbol | None = None
    for sym in symbols:
        if sym.span[0] <= span[0] and sym.span[1] >= span[1]:
            width = sym.span[1] - sym.span[0]
            if best is None or width < (best.span[1] - best.span[0]):
                best = sym
    return best.qualname if best is not None else None


def _find_following(
    span: tuple[int, int], symbols: tuple[RawSymbol, ...]
) -> str | None:
    """Symbol starting within 2 lines after the comment's end line, earliest first."""
    end = span[1]
    best: RawSymbol | None = None
    for sym in symbols:
        if end < sym.span[0] <= end + 2:
            if best is None or sym.span[0] < best.span[0]:
                best = sym
    return best.qualname if best is not None else None


# ------------------------------------------------------------------ imports
#
# frob.cycle needs raw import/include specifiers (unresolved -- "os.path",
# "local.h") to build its dependency graph; this is a second, narrower walk
# per language, kept here next to the symbol walkers so cycle detection
# never has to touch tree-sitter nodes directly (docs/lang.md).


def _python_import_specifiers(n: Node) -> list[str]:
    """Import specifiers declared by one python `import`/`from` statement node."""
    if n.type == "import_statement":
        return [child_text(child) for child in n.named_children]
    if n.type == "import_from_statement":
        mod = n.child_by_field_name("module_name")
        return [child_text(mod)] if mod is not None else []
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
                results.append(child_text(path_node).strip('"<>'))
        for child in n.children:
            visit(child)

    visit(root)
    return tuple(results)


_IMPORT_WALKERS = {
    "python": _imports_python,
    "c": _imports_c_family,
    "cpp": _imports_c_family,
}


# frob:doc docs/lang.md#extraction-api
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


# frob:doc docs/lang.md#extraction-api
def iter_identifiers(tree: Tree, language: str) -> tuple[tuple[str, int], ...]:
    """(name, 1-based line) for every identifier-like leaf (empty if unsupported)."""
    types = _IDENTIFIER_TYPES.get(language)
    if types is None:
        return ()
    out: list[tuple[str, int]] = []

    def visit(n: Node) -> None:
        if n.type in types:
            txt = child_text(n)
            if txt:
                out.append((txt, span_of(n)[0]))
            return
        for child in n.children:
            visit(child)

    visit(tree.root_node)
    return tuple(out)

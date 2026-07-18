"""Uniform parsing across six grammars (docs/modules/graph.md, Phase 1; T-0077).

`frob.graph` needs one shape -- symbols plus comments plus a content hash --
regardless of whether the source file is Python, TypeScript, Rust, C, C++,
or a `.strata` design file. Hand-rolling bespoke parsers (the fate of the
retired, Python-only predecessor module) means one place to fix every bug
per language and just as many places graph-level assumptions can silently
drift apart. `tree-sitter-language-pack` gives one grammar-loading
mechanism for the five code languages; this package gives one extraction
contract on top of it. `.strata` has no tree-sitter grammar, so it routes
through strata-core's own parser instead (`frob.lang._walk_strata`) but
produces the identical `ParsedFile` contract -- see `parse_file`.
Everything language-specific (node-type tables, publicness rules, doc-
comment conventions) lives in `_extract.py`'s per-language walkers or
`_walk_strata.py`; everything else (models, dispatch, hashing, the Result
boundary) lives here.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tree_sitter import Node, Tree
from tree_sitter_language_pack import get_parser
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.lang._common import child_by_field as _child_by_field
from frob.lang._common import child_text as _child_text
from frob.lang._common import export_tree as _export_tree
from frob.lang._common import iter_cpp_functions as _iter_cpp_functions
from frob.lang._extract import COMMENT_TYPES, extract
from frob.lang._extract import extract_imports as _extract_imports
from frob.lang._extract import iter_identifiers as _iter_identifiers
from frob.lang._models import ParsedFile, RawComment, RawSymbol, SymbolKind, TreeNode
from frob.lang._walk_strata import walk_strata as _walk_strata
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/lang.md#error-types
class LangError(ErrorSet):
    """Failure values `parse_file` can return -- never a bare exception."""

    UnsupportedLanguage = "File extension has no registered grammar"
    ParseFailed = "tree-sitter could not produce a usable tree"
    IoFailed = "File could not be read"


# extension -> (tree-sitter-language-pack grammar name, ParsedFile.language label)
_EXTENSION_TABLE: dict[str, tuple[str, str]] = {
    ".py": ("python", "python"),
    ".ts": ("typescript", "typescript"),
    ".tsx": ("tsx", "typescript"),
    ".rs": ("rust", "rust"),
    ".c": ("c", "c"),
    ".h": ("c", "c"),
    ".cpp": ("cpp", "cpp"),
    ".hpp": ("cpp", "cpp"),
    ".cc": ("cpp", "cpp"),
    ".hh": ("cpp", "cpp"),
    ".cxx": ("cpp", "cpp"),
}

# `.strata` has no tree-sitter grammar (`_parse`/`_EXTENSION_TABLE` below
# is tree-sitter-only) -- `parse_file` special-cases it through
# `frob.lang._walk_strata` instead (docs/modules/lang.md#strata, T-0077).
# It is still a first-class `frob.lang` language for every purpose
# `supported_languages()` signals: `parse_file` succeeds, symbols/comments
# come back, and `frob.graph`/`frob.check` can bind `frob:doc`/`frob:tests`
# to strata qualnames like any other grammar's. `extract_imports`,
# `iter_identifiers`, `raw_tree`, and `symbol_tree` are tree-sitter escape
# hatches with no strata analogue yet and return `Err(UnsupportedLanguage)`
# for `.strata` paths -- see each function's docstring.
_STRATA_EXTENSION = ".strata"
_STRATA_LANGUAGE = "strata"

_SUPPORTED_LANGUAGES = frozenset(
    label for _grammar, label in _EXTENSION_TABLE.values()
) | {_STRATA_LANGUAGE}


# frob:doc docs/modules/graph.md#public-api
def supported_languages() -> frozenset[str]:
    """The set of `ParsedFile.language` labels `parse_file` can ever produce."""
    return _SUPPORTED_LANGUAGES


def _display_path(path: Path) -> str:
    """Repo-relative POSIX path when possible, else the path as given."""
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


def _parse(path: Path) -> Result[tuple[Tree, bytes, str], LangError]:
    """Read and parse `path`, returning (tree, source, language_label).

    Shared by every public entry point below (`parse_file`, `extract_imports`,
    `iter_identifiers`) so the extension dispatch / read / tree-sitter-parse
    steps live in exactly one place.
    """
    ext = path.suffix.lower()
    entry = _EXTENSION_TABLE.get(ext)
    if entry is None:
        _log.warning("no grammar registered for extension %r (path=%s)", ext, path)
        return Err(LangError.UnsupportedLanguage)
    grammar_name, language_label = entry
    _log.debug("dispatching path=%s to grammar=%s", path, grammar_name)

    try:
        source = path.read_bytes()
    except OSError as exc:
        _log.error("failed to read %s: %s", path, exc)
        return Err(LangError.IoFailed)

    parser = get_parser(grammar_name)  # type: ignore[arg-type]
    tree = parser.parse(source)
    unusable = tree.root_node is None or (
        tree.root_node.has_error and tree.root_node.child_count == 0
    )
    if unusable:
        _log.error("tree-sitter produced no usable tree for %s", path)
        return Err(LangError.ParseFailed)

    return Ok((tree, source, language_label))


def _build_parsed_file(
    path: Path,
    language_label: str,
    symbols: tuple[RawSymbol, ...],
    comments: tuple[RawComment, ...],
    content_bytes: bytes,
) -> ParsedFile:
    """Assemble and log a `ParsedFile` -- the tail both `parse_file` branches share."""
    parsed = ParsedFile(
        path=_display_path(path),
        language=language_label,
        symbols=symbols,
        comments=comments,
        content_hash=hashlib.sha256(content_bytes).hexdigest(),
    )
    _log.info(
        "parsed %s: language=%s symbols=%d comments=%d",
        parsed.path,
        language_label,
        len(symbols),
        len(comments),
    )
    return parsed


# frob:doc docs/modules/graph.md#public-api
def _parse_strata_file(path: Path) -> Result[ParsedFile, LangError]:
    """`parse_file`'s `.strata` branch -- strata-core validation, no tree-sitter.

    Mirrors `parse_file`'s tree-sitter branch shape (read -> extract ->
    hash -> log -> `ParsedFile`, via the shared `_build_parsed_file` tail)
    so both branches produce an identical contract for `frob.graph`, just
    with `frob.lang._walk_strata.walk_strata` standing in for `extract`.
    """
    try:
        source_bytes = path.read_bytes()
    except OSError as exc:
        _log.error("failed to read %s: %s", path, exc)
        return Err(LangError.IoFailed)

    walked = _walk_strata(source_bytes.decode("utf-8", errors="replace"))
    if walked.is_err:
        _log.error("strata parse failed for %s: %s", path, walked.danger_err)
        return Err(LangError.ParseFailed)
    symbols, comments = walked.danger_ok
    parsed = _build_parsed_file(path, _STRATA_LANGUAGE, symbols, comments, source_bytes)
    return Ok(parsed)


# frob:doc docs/modules/graph.md#public-api
def parse_file(path: Path) -> Result[ParsedFile, LangError]:
    """Read, parse, and extract `path` into a `ParsedFile` (dispatch by extension).

    `.strata` files route through `_parse_strata_file` (strata-core's own
    parser, no tree-sitter grammar exists for the language); every other
    extension routes through the tree-sitter `_parse`/`extract` pair below.
    """
    if path.suffix.lower() == _STRATA_EXTENSION:
        return _parse_strata_file(path)

    parsed_result = _parse(path)
    if parsed_result.is_err:
        return Err(parsed_result.danger_err)
    tree, source, language_label = parsed_result.danger_ok

    symbols, comments = extract(tree, source, language_label)
    return Ok(_build_parsed_file(path, language_label, symbols, comments, source))


# frob:doc docs/modules/graph.md#public-api
def extract_imports(path: Path) -> Result[tuple[str, ...], LangError]:
    """Raw, unresolved import/include specifiers declared in `path`.

    `frob.cycle` uses this to build its dependency graph -- specifiers come
    back exactly as written in source (a dotted python module name, a quoted
    C/C++ include path); resolving one to a real file under a scan root is
    the caller's job (see `resolve_local_import`), not this parser's.
    """
    parsed_result = _parse(path)
    if parsed_result.is_err:
        return Err(parsed_result.danger_err)
    tree, _source, language_label = parsed_result.danger_ok
    specifiers = _extract_imports(tree, language_label)
    _log.debug("extracted %d import specifiers from %s", len(specifiers), path)
    return Ok(specifiers)


# frob:doc docs/modules/graph.md#public-api
def iter_identifiers(path: Path) -> Result[tuple[tuple[str, int], ...], LangError]:
    """(name, 1-based line) for every identifier-like leaf token in `path`.

    `frob.xref` uses this to find usages of a symbol -- a broader, flatter
    shape than `RawSymbol` (which only covers declarations), so it is kept
    as its own extraction rather than folded into `parse_file`.
    """
    parsed_result = _parse(path)
    if parsed_result.is_err:
        return Err(parsed_result.danger_err)
    tree, _source, language_label = parsed_result.danger_ok
    return Ok(_iter_identifiers(tree, language_label))


# frob:doc docs/modules/graph.md#public-api
def raw_tree(path: Path) -> Result[tuple[Tree, bytes, str], LangError]:
    """The raw tree-sitter `(Tree, source_bytes, language_label)` for `path`.

    An escape hatch for callers that need node-level tree-sitter access
    (`frob.arch`'s structural metric walks, `frob.dup._legacy`'s Type-1/2
    scanner) without standing up a second `get_parser`/`Parser.parse` call
    site of their own -- every grammar load in the process still goes
    through this module's single `_parse` dispatch table. Prefer
    `parse_file`/`extract_imports`/`iter_identifiers` when the normalized
    shape is enough; reach for `raw_tree` only when a caller genuinely needs
    tree-sitter's `Node` API (field lookups, byte spans) directly.
    """
    return _parse(path)


# frob:doc docs/modules/graph.md#public-api
def cpp_function_nodes(tree: Tree) -> tuple[tuple[Node, str], ...]:
    """(node, qualified_name) for every C/C++ function in `tree` (one level
    of class/struct nesting). Thin public wrapper around
    `frob.lang._common.iter_cpp_functions` -- see its docstring for the
    exact walk semantics `frob.arch` and `frob.dup._legacy` share."""
    return _iter_cpp_functions(tree.root_node)


# frob:doc docs/modules/graph.md#public-api
def child_by_field(node: Node, field: str) -> Node | None:
    """`node.child_by_field_name(field)`, exposed so `frob.arch` and
    `frob.dup._legacy`'s raw-node walks share one field-lookup call
    instead of each keeping a local copy (see `frob.lang._common`)."""
    return _child_by_field(node, field)


# frob:doc docs/modules/graph.md#public-api
def node_text(node: Node | None) -> str:
    """Decode `node`'s own text, or '' if absent. Public alias of
    `frob.lang._common.child_text` for callers doing raw node traversal
    outside the extraction pipeline (`frob.arch`, `frob.dup._legacy`)."""
    return _child_text(node)


# frob:doc docs/modules/dup.md#public-api
def symbol_tree(path: Path, span: tuple[int, int]) -> Result[TreeNode, LangError]:
    """The `TreeNode` subtree covering `span` (1-based, inclusive lines) in `path`.

    `frob.dup`'s R4 rung calls this with a `RawSymbol.span` (from an earlier
    `parse_file`) to get real node structure for `frob-core`'s Zhang-Shasha
    tree-edit-distance kernel, instead of the flat `body_tokens` sequence.
    Re-parses `path` (a second `_parse` call for the same file `parse_file`
    already visited) -- acceptable here since `frob.dup._pipeline` calls
    this only for R4 candidate pairs already surfaced by cheaper rungs, not
    for every symbol in a scan.
    """
    parsed_result = _parse(path)
    if parsed_result.is_err:
        return Err(parsed_result.danger_err)
    tree, _source, language_label = parsed_result.danger_ok
    start_line, end_line = span
    start_point = (max(start_line - 1, 0), 0)
    # A too-large end column makes some tree-sitter bindings fall back to
    # the whole-tree root instead of the smallest enclosing node -- probe a
    # single point first, then climb parents until the span is covered.
    node = tree.root_node.descendant_for_point_range(start_point, start_point)
    if node is None:
        node = tree.root_node
    while node.parent is not None and node.end_point[0] < end_line - 1:
        node = node.parent
    comment_types = COMMENT_TYPES.get(language_label, frozenset())
    return Ok(_export_tree(node, comment_types))


# frob:doc docs/modules/graph.md#public-api
def resolve_local_import(
    specifier: str, language: str, *, file_dir: Path, root: Path
) -> str | None:
    """Resolve a raw `extract_imports` specifier to a `root`-relative path.

    Returns `None` when the specifier does not point at a file that exists
    under `root` (a third-party import, a system `<...>` include already
    filtered out upstream, etc.) -- `frob.cycle` skips those rather than
    adding a graph edge to nowhere.
    """
    if language == "python":
        base = specifier.replace(".", "/")
        for suffix in (".py", "/__init__.py"):
            candidate = Path(base + suffix)
            if (root / candidate).exists():
                return candidate.as_posix()
        return None
    if language in ("c", "cpp"):
        candidate = (file_dir / specifier).resolve()
        try:
            rel = candidate.relative_to(root.resolve())
        except ValueError:
            return None
        return rel.as_posix() if candidate.exists() else None
    return None


__all__ = [
    "LangError",
    "ParsedFile",
    "RawComment",
    "RawSymbol",
    "SymbolKind",
    "child_by_field",
    "cpp_function_nodes",
    "extract_imports",
    "iter_identifiers",
    "node_text",
    "parse_file",
    "raw_tree",
    "resolve_local_import",
    "supported_languages",
    "symbol_tree",
    "TreeNode",
]

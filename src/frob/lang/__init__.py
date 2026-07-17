"""Uniform tree-sitter parsing across five languages (docs/graph.md, Phase 1).

`frob.graph` needs one shape -- symbols plus comments plus a content hash --
regardless of whether the source file is Python, TypeScript, Rust, C, or
C++. Hand-rolling five bespoke parsers (the fate of the old, Python-only
`frob.ast`) means five places to fix every bug and five places graph-level
assumptions can silently drift apart. `tree-sitter-language-pack` gives one
grammar-loading mechanism for all five; this package gives one extraction
contract on top of it. Everything language-specific (node-type tables,
publicness rules, doc-comment conventions) lives in `_extract.py`'s per-
language walkers; everything else (models, dispatch, hashing, the Result
boundary) lives here.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from tree_sitter import Tree
from tree_sitter_language_pack import get_parser
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.lang._extract import extract
from frob.lang._extract import extract_imports as _extract_imports
from frob.lang._extract import iter_identifiers as _iter_identifiers
from frob.lang._models import ParsedFile, RawComment, RawSymbol, SymbolKind
from frob.logging import get_logger

_log = get_logger(__name__)


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
}

_SUPPORTED_LANGUAGES = frozenset(label for _grammar, label in _EXTENSION_TABLE.values())


# frob:doc docs/graph.md#public-api
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


# frob:doc docs/graph.md#public-api
def parse_file(path: Path) -> Result[ParsedFile, LangError]:
    """Read, parse, and extract `path` into a `ParsedFile` (dispatch by extension)."""
    parsed_result = _parse(path)
    if parsed_result.is_err:
        return Err(parsed_result.danger_err)
    tree, source, language_label = parsed_result.danger_ok

    symbols, comments = extract(tree, source, language_label)
    content_hash = hashlib.sha256(source).hexdigest()
    parsed = ParsedFile(
        path=_display_path(path),
        language=language_label,
        symbols=symbols,
        comments=comments,
        content_hash=content_hash,
    )
    _log.info(
        "parsed %s: language=%s symbols=%d comments=%d",
        parsed.path,
        language_label,
        len(symbols),
        len(comments),
    )
    return Ok(parsed)


# frob:doc docs/graph.md#public-api
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


# frob:doc docs/graph.md#public-api
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


# frob:doc docs/graph.md#public-api
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
    "extract_imports",
    "iter_identifiers",
    "parse_file",
    "resolve_local_import",
    "supported_languages",
]

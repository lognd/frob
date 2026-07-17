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

from tree_sitter_language_pack import get_parser
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.lang._extract import extract
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


# frob:doc docs/graph.md#public-api
def parse_file(path: Path) -> Result[ParsedFile, LangError]:
    """Read, parse, and extract `path` into a `ParsedFile` (dispatch by extension)."""
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

    symbols, comments = extract(tree, source, grammar_name)
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


__all__ = [
    "LangError",
    "ParsedFile",
    "RawComment",
    "RawSymbol",
    "SymbolKind",
    "parse_file",
    "supported_languages",
]

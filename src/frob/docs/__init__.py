from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from frob.excludes import iter_files

if TYPE_CHECKING:
    from frob.lang._models import RawSymbol


# frob:doc docs/modules/app.md#frobdocs-library
class Docstring(BaseModel):
    symbol: str
    kind: str
    line: int
    text: str


# frob:doc docs/modules/app.md#frobdocs-library
class DocEntry(BaseModel):
    heading: str
    summary: str
    file: str
    line: int


# frob:doc docs/modules/app.md#frobdocs-library
class DocMatch(BaseModel):
    file: str
    line: int
    heading: str
    excerpt: str


class _SymbolFilters(BaseModel):
    """The class/method/function name filters derived from a `symbol` query."""

    class_filter: str | None = None
    method_filter: str | None = None
    func_filter: str | None = None


def _symbol_filters(symbol: str | None) -> _SymbolFilters:
    """Split a `symbol` query into class/method/function name filters."""
    if symbol is None:
        return _SymbolFilters()
    if "." in symbol:
        cls, _, method = symbol.partition(".")
        return _SymbolFilters(class_filter=cls, method_filter=method)
    return _SymbolFilters(class_filter=symbol, func_filter=symbol)


def _method_docstring(sym: RawSymbol, filters: _SymbolFilters) -> Docstring | None:
    """The `Docstring` for a method symbol under `filters`, or None if filtered."""
    owner, _, mname = sym.qualname.rpartition(".")
    if filters.class_filter is not None and owner != filters.class_filter:
        return None
    if filters.method_filter is not None and mname != filters.method_filter:
        return None
    return Docstring(
        symbol=sym.qualname, kind="method", line=sym.span[0], text=sym.doc_text
    )


def _docstring_for_symbol(sym: RawSymbol, filters: _SymbolFilters) -> Docstring | None:
    """The `Docstring` for one parsed symbol under `filters`, or None if filtered."""
    from frob.lang import SymbolKind

    if not sym.doc_text:
        return None
    if sym.kind == SymbolKind.FUNCTION:
        if filters.func_filter is not None and sym.qualname != filters.func_filter:
            return None
        if filters.class_filter is not None and filters.func_filter is None:
            return None
        return Docstring(
            symbol=sym.qualname, kind="function", line=sym.span[0], text=sym.doc_text
        )
    if sym.kind == SymbolKind.CLASS and "." not in sym.qualname:
        if filters.class_filter is not None and sym.qualname != filters.class_filter:
            return None
        if filters.method_filter is None:
            return Docstring(
                symbol=sym.qualname, kind="class", line=sym.span[0], text=sym.doc_text
            )
        return None
    if sym.kind == SymbolKind.METHOD:
        return _method_docstring(sym, filters)
    return None


# frob:doc docs/modules/app.md#frobdocs-library
# frob:tests tests/unit/test_docs_module.py::test_extract_docstrings
# frob:tests \
# tests/unit/test_docs_module.py::test_extract_docstrings_non_python_file_returns_empty
# frob:tests \
# tests/unit/test_docs_module.py::test_extract_docstrings_parse_failure_returns_empty
# frob:tests \
# tests/unit/test_docs_module.py::test_extract_docstrings_symbol_filter_narrows_to_one_\
# method
def extract_docstrings(path: Path, symbol: str | None = None) -> list[Docstring]:
    """Every python docstring in `path` (module, class, function, method).

    Rebuilt on top of `frob.lang.parse_file`'s `RawSymbol.doc_text` -- that
    field is already whitespace-collapsed (`_common._collapse_ws`), so the
    `text` returned here is a single-line rendering rather than the old
    tree-sitter walker's multi-line, quote-stripped one. `frob.docs` only
    ever displays or greps this text, never round-trips it, so the shape
    change is invisible to callers.
    """
    from frob.lang import parse_file

    result = parse_file(path)
    if result.is_err:
        return []
    parsed = result.danger_ok
    if parsed.language != "python":
        return []

    filters = _symbol_filters(symbol)
    results: list[Docstring] = _module_entries(path, symbol)
    for sym in parsed.symbols:
        doc = _docstring_for_symbol(sym, filters)
        if doc is not None:
            results.append(doc)
    return results


def _module_entries(path: Path, symbol: str | None) -> list[Docstring]:
    """The module-level docstring row for `path`, unless a `symbol` filter is set."""
    if symbol is not None:
        return []
    module_doc = _module_docstring(path)
    if module_doc is None:
        return []
    line, text = module_doc
    return [Docstring(symbol="module", kind="module", line=line, text=text)]


def _module_docstring(path: Path) -> tuple[int, str] | None:
    """The module-level docstring's (line, collapsed text), if present.

    `RawSymbol`/`RawComment` do not carry a module docstring (it is neither
    a declaration nor a comment) -- python's own `ast` module handles this
    one case cheaply and correctly without a second tree-sitter pass.
    """
    import ast as _pyast

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = _pyast.parse(source)
        doc = _pyast.get_docstring(tree, clean=True)
        if doc is None or not tree.body:
            return None
        first = tree.body[0]
        line = getattr(first, "lineno", 1)
        return line, " ".join(doc.split())
    except Exception:
        return None


# frob:doc docs/modules/app.md#frobdocs-library
# frob:tests tests/unit/test_docs_module.py::test_find_docs_dir
# frob:tests tests/unit/test_docs_module.py::test_find_docs_dir_not_found_returns_none  # noqa: E501
def find_docs_dir(start: Path) -> Path | None:
    current = start if start.is_dir() else start.parent
    for _ in range(8):
        candidate = current / "docs"
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _md_headings_and_summaries(md_path: Path) -> list[tuple[int, str, str]]:
    entries: list[tuple[int, str, str]] = []
    lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^#{1,6}\s+(.*)", line)
        if m:
            heading = m.group(1).strip()
            line_no = i + 1
            i += 1
            para_lines: list[str] = []
            while i < len(lines) and not re.match(r"^#{1,6}\s+", lines[i]):
                s = lines[i].strip()
                if s:
                    para_lines.append(s)
                elif para_lines:
                    break
                i += 1
            summary = " ".join(para_lines)
            entries.append((line_no, heading, summary))
        else:
            i += 1
    return entries


# frob:doc docs/modules/app.md#frobdocs-library
# frob:tests tests/unit/test_docs_module.py::test_overview
# frob:tests \
# tests/unit/test_docs_module.py::test_overview_no_keyword_match_falls_back_to_all_entr\
# ies
# frob:tests tests/unit/test_docs_module.py::test_overview_symbol_keyword_narrows_match  # noqa: E501
def overview(path: Path, symbol: str | None = None) -> list[DocEntry]:
    docs_dir = find_docs_dir(path)
    if not docs_dir:
        return []

    stem = path.stem if not path.is_dir() else path.name
    keywords: list[str] = [w.lower() for w in re.split(r"[_\-\s]+", stem) if w]
    if symbol:
        for part in re.split(r"[_\-\.\s]+", symbol):
            w = part.lower()
            if w and w not in keywords:
                keywords.append(w)

    all_entries = _collect_doc_entries(docs_dir)
    results = [e for e in all_entries if _entry_matches(e, keywords)]
    if not results:
        return all_entries
    return results


def _collect_doc_entries(docs_dir: Path) -> list[DocEntry]:
    """Every heading/summary in `docs_dir` as `DocEntry` rows, file-sorted."""
    md_files = sorted(iter_files(docs_dir, suffix=".md"))
    entries: list[DocEntry] = []
    for md_file in md_files:
        for line_no, heading, summary in _md_headings_and_summaries(md_file):
            entries.append(
                DocEntry(
                    heading=heading,
                    summary=summary,
                    file=str(md_file),
                    line=line_no,
                )
            )
    return entries


def _entry_matches(entry: DocEntry, keywords: list[str]) -> bool:
    """Whether any of `keywords` appears in the entry's heading or summary."""
    combined = (entry.heading + " " + entry.summary).lower()
    return any(kw in combined for kw in keywords)


# frob:doc docs/modules/app.md#frobdocs-library
# frob:tests tests/unit/test_docs_module.py::test_search
# frob:tests \
# tests/unit/test_docs_module.py::test_search_tracks_heading_and_joins_surrounding_lines
def search(query: str, docs_dir: Path) -> list[DocMatch]:
    q = query.lower()
    results: list[DocMatch] = []

    md_files = sorted(iter_files(docs_dir, suffix=".md"))
    for md_file in md_files:
        lines = md_file.read_text(encoding="utf-8", errors="replace").splitlines()
        current_heading = ""
        for i, line in enumerate(lines):
            m = re.match(r"^#{1,6}\s+(.*)", line)
            if m:
                current_heading = m.group(1).strip()
            if q in line.lower():
                before = lines[i - 1].strip() if i > 0 else ""
                after = lines[i + 1].strip() if i + 1 < len(lines) else ""
                parts = [line.strip()]
                if before and not re.match(r"^#{1,6}\s+", before):
                    parts = [before] + parts
                if after and not re.match(r"^#{1,6}\s+", after):
                    parts = parts + [after]
                excerpt = " | ".join(parts)
                results.append(
                    DocMatch(
                        file=str(md_file),
                        line=i + 1,
                        heading=current_heading,
                        excerpt=excerpt,
                    )
                )

    return results

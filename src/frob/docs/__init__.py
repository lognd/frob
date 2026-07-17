from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel


class Docstring(BaseModel):
    symbol: str
    kind: str
    line: int
    text: str


class DocEntry(BaseModel):
    heading: str
    summary: str
    file: str
    line: int


class DocMatch(BaseModel):
    file: str
    line: int
    heading: str
    excerpt: str


def extract_docstrings(path: Path, symbol: str | None = None) -> list[Docstring]:
    """Every python docstring in `path` (module, class, function, method).

    Rebuilt on top of `frob.lang.parse_file`'s `RawSymbol.doc_text` -- that
    field is already whitespace-collapsed (`_common.collapse_ws`), so the
    `text` returned here is a single-line rendering rather than the old
    tree-sitter walker's multi-line, quote-stripped one. `frob.docs` only
    ever displays or greps this text, never round-trips it, so the shape
    change is invisible to callers.
    """
    from frob.lang import SymbolKind, parse_file

    result = parse_file(path)
    if result.is_err:
        return []
    parsed = result.danger_ok
    if parsed.language != "python":
        return []

    results: list[Docstring] = []

    class_filter: str | None = None
    method_filter: str | None = None
    func_filter: str | None = None

    if symbol is not None:
        if "." in symbol:
            parts = symbol.split(".", 1)
            class_filter = parts[0]
            method_filter = parts[1]
        else:
            class_filter = symbol
            func_filter = symbol

    if symbol is None:
        module_doc = _module_docstring(path)
        if module_doc is not None:
            line, text = module_doc
            results.append(
                Docstring(symbol="module", kind="module", line=line, text=text)
            )

    for sym in parsed.symbols:
        if not sym.doc_text:
            continue
        if sym.kind == SymbolKind.FUNCTION:
            if func_filter is not None and sym.qualname != func_filter:
                continue
            if class_filter is not None and func_filter is None:
                continue
            results.append(
                Docstring(
                    symbol=sym.qualname,
                    kind="function",
                    line=sym.span[0],
                    text=sym.doc_text,
                )
            )
        elif sym.kind == SymbolKind.CLASS and "." not in sym.qualname:
            if class_filter is not None and sym.qualname != class_filter:
                continue
            if method_filter is None:
                results.append(
                    Docstring(
                        symbol=sym.qualname,
                        kind="class",
                        line=sym.span[0],
                        text=sym.doc_text,
                    )
                )
        elif sym.kind == SymbolKind.METHOD:
            owner, _, mname = sym.qualname.rpartition(".")
            if class_filter is not None and owner != class_filter:
                continue
            if method_filter is not None and mname != method_filter:
                continue
            results.append(
                Docstring(
                    symbol=sym.qualname,
                    kind="method",
                    line=sym.span[0],
                    text=sym.doc_text,
                )
            )

    return results


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
    except (OSError, SyntaxError):
        return None
    doc = _pyast.get_docstring(tree, clean=True)
    if doc is None or not tree.body:
        return None
    first = tree.body[0]
    line = getattr(first, "lineno", 1)
    return line, " ".join(doc.split())


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

    results: list[DocEntry] = []
    all_entries: list[DocEntry] = []

    for md_file in sorted(docs_dir.rglob("*.md")):
        for line_no, heading, summary in _md_headings_and_summaries(md_file):
            entry = DocEntry(
                heading=heading,
                summary=summary,
                file=str(md_file),
                line=line_no,
            )
            all_entries.append(entry)
            combined = (heading + " " + summary).lower()
            if any(kw in combined for kw in keywords):
                results.append(entry)

    if not results:
        return all_entries
    return results


def search(query: str, docs_dir: Path) -> list[DocMatch]:
    q = query.lower()
    results: list[DocMatch] = []

    for md_file in sorted(docs_dir.rglob("*.md")):
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

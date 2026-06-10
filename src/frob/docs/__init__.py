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


def _strip_docstring(raw: str) -> str:
    for delim in ('"""', "'''"):
        if raw.startswith(delim) and raw.endswith(delim) and len(raw) >= 6:
            inner = raw[3:-3]
            lines = inner.splitlines()
            stripped = [l.strip() for l in lines]
            while stripped and not stripped[0]:
                stripped.pop(0)
            while stripped and not stripped[-1]:
                stripped.pop()
            return "\n".join(stripped)
    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        return raw[1:-1]
    return raw


def _first_docstring_child(body_node):
    if body_node is None:
        return None
    for child in body_node.named_children:
        if child.type == "expression_statement":
            for sub in child.named_children:
                if sub.type == "string":
                    return sub
        break
    return None


def extract_docstrings(path: Path, symbol: str | None = None) -> list[Docstring]:
    from frob.ast import python as _py
    from frob.ast.common import child_by_field, text

    try:
        src, tree = _py.parse_file(path)
    except Exception:
        return []

    results: list[Docstring] = []
    root = tree.root_node

    if symbol is None:
        ds = _first_docstring_child(root)
        if ds:
            raw = text(ds)
            results.append(
                Docstring(
                    symbol="module",
                    kind="module",
                    line=ds.start_point[0] + 1,
                    text=_strip_docstring(raw),
                )
            )

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

    for node in root.children:
        if node.type == "function_definition":
            name_node = child_by_field(node, "name")
            if name_node is None:
                continue
            fname = text(name_node)
            if func_filter is not None and fname != func_filter:
                continue
            if class_filter is not None and func_filter is None:
                continue
            body = child_by_field(node, "body")
            ds = _first_docstring_child(body)
            if ds:
                raw = text(ds)
                results.append(
                    Docstring(
                        symbol=fname,
                        kind="function",
                        line=ds.start_point[0] + 1,
                        text=_strip_docstring(raw),
                    )
                )

        elif node.type == "class_definition":
            name_node = child_by_field(node, "name")
            if name_node is None:
                continue
            cname = text(name_node)
            if class_filter is not None and cname != class_filter:
                continue

            body = child_by_field(node, "body")
            if method_filter is None:
                ds = _first_docstring_child(body)
                if ds:
                    raw = text(ds)
                    results.append(
                        Docstring(
                            symbol=cname,
                            kind="class",
                            line=ds.start_point[0] + 1,
                            text=_strip_docstring(raw),
                        )
                    )

            if body:
                for child in body.named_children:
                    if child.type == "function_definition":
                        mname_node = child_by_field(child, "name")
                        if mname_node is None:
                            continue
                        mname = text(mname_node)
                        if method_filter is not None and mname != method_filter:
                            continue
                        mbody = child_by_field(child, "body")
                        ds = _first_docstring_child(mbody)
                        if ds:
                            raw = text(ds)
                            results.append(
                                Docstring(
                                    symbol=f"{cname}.{mname}",
                                    kind="method",
                                    line=ds.start_point[0] + 1,
                                    text=_strip_docstring(raw),
                                )
                            )

    return results


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

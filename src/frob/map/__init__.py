from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from frob.outline import outline_file, ModuleOutline

_SOURCE_EXTS = {".py", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"}


class FileNode(BaseModel):
    path: str
    lines: int
    symbols: list[str]


class MapResult(BaseModel):
    root: str
    total_files: int
    total_lines: int
    files: list[FileNode]

    def as_text(self, max_symbols: int = 6) -> str:
        lines: list[str] = [
            f"{self.root}  ({self.total_files} files, {self.total_lines:,} lines)"
        ]
        # Group by directory
        prev_dir = ""
        for node in self.files:
            p = Path(node.path)
            dir_part = str(p.parent)
            if dir_part != prev_dir:
                if dir_part != ".":
                    lines.append(f"  {dir_part}/")
                prev_dir = dir_part
            indent = "    " if dir_part != "." else "  "
            sym_str = ""
            if node.symbols:
                shown = node.symbols[:max_symbols]
                sym_str = "  " + ", ".join(shown)
                if len(node.symbols) > max_symbols:
                    sym_str += f" ... (+{len(node.symbols) - max_symbols})"
            lines.append(f"{indent}{p.name:<30} {node.lines:>4}L{sym_str}")
        return "\n".join(lines)

    def as_json(self) -> str:
        return self.model_dump_json(indent=2)


def map_project(root: Path, depth: int | None = None) -> MapResult:
    """
    Walk root recursively (respecting depth) and outline every source file.
    Unknown file types are counted for line totals but have empty symbol lists.
    """
    files: list[FileNode] = []

    root = root.resolve()
    all_paths = _collect_paths(root, depth)

    for path in sorted(all_paths):
        rel = str(path.relative_to(root))
        ext = path.suffix.lower()

        if ext in _SOURCE_EXTS:
            result = outline_file(path)
            if result.is_ok:
                ol = result.danger_ok
                symbols = _symbols_from_outline(ol)
                lines = ol.lines
            else:
                lines = _count_lines(path)
                symbols = []
        else:
            lines = _count_lines(path)
            symbols = []

        files.append(FileNode(path=rel, lines=lines, symbols=symbols))

    total_lines = sum(f.lines for f in files)
    return MapResult(
        root=str(root),
        total_files=len(files),
        total_lines=total_lines,
        files=files,
    )


def _collect_paths(root: Path, depth: int | None) -> list[Path]:
    results: list[Path] = []
    _walk(root, root, 0, depth, results)
    return results


def _walk(root: Path, current: Path, current_depth: int, max_depth: int | None, out: list[Path]) -> None:
    for child in sorted(current.iterdir()):
        if child.name.startswith(".") or child.name in ("__pycache__", "node_modules", ".venv"):
            continue
        if child.is_file() and child.suffix.lower() in _SOURCE_EXTS:
            out.append(child)
        elif child.is_dir():
            if max_depth is None or current_depth < max_depth:
                _walk(root, child, current_depth + 1, max_depth, out)


def _symbols_from_outline(ol: ModuleOutline) -> list[str]:
    syms: list[str] = []
    for fn in ol.functions:
        syms.append(fn.name)
    for cls in ol.classes:
        syms.append(cls.name)
    return syms


def _count_lines(path: Path) -> int:
    try:
        return path.read_bytes().count(b"\n") + 1
    except Exception:
        return 0

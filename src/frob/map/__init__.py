from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from frob.outline import ModuleOutline, outline_file

_SOURCE_EXTS = {".py", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"}

# Conservative estimate: code is denser than prose (~3.5 chars/token for
# typical Python/C++; prose is ~4). We round down to avoid surprises.
_CHARS_PER_TOKEN = 3.5


def _estimate_tokens(text: str | bytes) -> int:
    """Rough token-count estimate from character count (no tokenizer dep)."""
    if isinstance(text, bytes):
        text = text.decode(errors="replace")
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


# frob:doc docs/commands/map.md#public-api
class FileNode(BaseModel):
    path: str
    lines: int
    tokens: int
    symbols: list[str]
    private_count: int = 0


# frob:doc docs/commands/map.md#public-api
class MapResult(BaseModel):
    root: str
    total_files: int
    total_lines: int
    files: list[FileNode]

    # frob:ticket T-0588
    # frob:tests tests/unit/test_map.py::test_map_as_text
    def as_text(self, max_symbols: int = 6, include_private: bool = False) -> str:
        # frob:doc docs/commands/map.md#public-api
        lines: list[str] = [
            f"{self.root}  ({self.total_files} files, {self.total_lines:,} lines)"
        ]
        prev_dir = ""
        for node in self.files:
            p = Path(node.path)
            dir_part = str(p.parent)
            if dir_part != prev_dir:
                if dir_part != ".":
                    lines.append(f"  {dir_part}/")
                prev_dir = dir_part
            indent = "    " if dir_part != "." else "  "
            sym_str = _format_symbols(node, max_symbols, include_private)
            lines.append(
                f"{indent}{p.name:<30} {node.lines:>4}L  ~{node.tokens:>5} tok{sym_str}"
            )
        return "\n".join(lines)

    # frob:ticket T-0588
    # frob:tests tests/unit/test_map.py::test_map_as_json
    def as_json(self) -> str:
        # frob:doc docs/commands/map.md#public-api
        return self.model_dump_json(indent=2)


def _truncated_symbols(syms: list[str], max_symbols: int) -> str:
    """First `max_symbols` names joined, with a `... (+N)` overflow marker."""
    shown = ", ".join(syms[:max_symbols])
    extra = len(syms) - max_symbols
    return shown + (f" ... (+{extra})" if extra > 0 else "")


def _public_symbols_summary(pub: list[str], priv: int, max_symbols: int) -> str:
    """Public-symbol summary with a trailing private count (the default view)."""
    if not pub and not priv:
        return ""
    if priv <= 0:
        return "  " + _truncated_symbols(pub, max_symbols)
    pub_part = ", ".join(pub[:max_symbols])
    if pub_part:
        return f"  [{len(pub)} pub: {pub_part} | {priv} priv]"
    return f"  [{priv} priv]"


def _format_symbols(node: FileNode, max_symbols: int, include_private: bool) -> str:
    """The trailing symbol summary for one file row of the map."""
    if include_private:
        if not node.symbols:
            return ""
        return "  " + _truncated_symbols(node.symbols, max_symbols)
    return _public_symbols_summary(node.symbols, node.private_count, max_symbols)


def _file_node(root: Path, path: Path) -> FileNode:
    """The `FileNode` (lines/tokens/symbols) for one file under `root`."""
    rel = str(path.relative_to(root))
    ext = path.suffix.lower()

    if ext in _SOURCE_EXTS:
        result = outline_file(path)
        if result.is_ok:
            ol = result.danger_ok
            pub_syms, priv_count = _symbols_from_outline(ol)
            lines = ol.lines
        else:
            lines = _count_lines(path)
            pub_syms, priv_count = [], 0
    else:
        lines = _count_lines(path)
        pub_syms, priv_count = [], 0

    try:
        tok = _estimate_tokens(path.read_bytes())
    except Exception:
        tok = 0

    return FileNode(
        path=rel, lines=lines, tokens=tok, symbols=pub_syms, private_count=priv_count
    )


def _display_root(root: Path) -> str:
    """`root` relative to the cwd when possible, else `root` unchanged."""
    try:
        return str(root.relative_to(Path.cwd()))
    except ValueError:
        return str(root)


# frob:doc docs/commands/map.md#public-api
def map_project(root: Path, depth: int | None = None) -> MapResult:
    root = root.resolve()
    all_paths = sorted(_collect_paths(root, depth))
    files = [_file_node(root, path) for path in all_paths]

    total_lines = sum(f.lines for f in files)
    return MapResult(
        root=_display_root(root),
        total_files=len(files),
        total_lines=total_lines,
        files=files,
    )


def _collect_paths(root: Path, depth: int | None) -> list[Path]:
    results: list[Path] = []
    _walk(root, root, 0, depth, results)
    return results


def _walk(
    root: Path,
    current: Path,
    current_depth: int,
    max_depth: int | None,
    out: list[Path],
) -> None:
    children = sorted(current.iterdir())
    for child in children:
        if child.name.startswith(".") or child.name in (
            "__pycache__",
            "node_modules",
            ".venv",
        ):
            continue
        if child.is_file() and child.suffix.lower() in _SOURCE_EXTS:
            out.append(child)
        elif child.is_dir():
            if max_depth is None or current_depth < max_depth:
                # frob:invariant terminates reason="child is a strict subdirectory of current on the real filesystem tree (no symlink traversal here), and current_depth is bounded above by max_depth when given" measure="max_depth is not None: max_depth - current_depth strictly decreases; max_depth is None: bounded by the finite depth of the real directory tree"  # noqa: E501
                _walk(root, child, current_depth + 1, max_depth, out)


def _symbols_from_outline(ol: ModuleOutline) -> tuple[list[str], int]:
    pub: list[str] = []
    priv_count = 0
    for fn in ol.functions:
        if fn.name.startswith("_"):
            priv_count += 1
        else:
            pub.append(fn.name)
    for cls in ol.classes:
        if cls.name.startswith("_"):
            priv_count += 1
        else:
            pub.append(cls.name)
    return pub, priv_count


def _count_lines(path: Path) -> int:
    try:
        return path.read_bytes().count(b"\n") + 1
    except Exception:
        return 0

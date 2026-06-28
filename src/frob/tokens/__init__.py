from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

# Conservative estimate: code is denser than prose (~3.5 chars/token for
# typical Python/C++; prose is ~4). We round down to avoid surprises.
_CHARS_PER_TOKEN = 3.5

_SOURCE_EXTS = {
    ".py",
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hpp",
    ".hxx",
    ".md",
    ".toml",
}


class RegionCost(BaseModel):
    name: str
    start_line: int
    end_line: int
    tokens: int


class FileCost(BaseModel):
    path: str
    chars: int
    tokens: int
    regions: list[RegionCost]

    def as_text(self, detail: bool = False) -> str:
        line = f"{self.path:<50} ~{self.tokens:>6,} tokens"
        if not detail or not self.regions:
            return line
        parts = [line]
        for r in self.regions:
            parts.append(
                f"  {r.name:<40} ~{r.tokens:>5,} tok  [L{r.start_line}-L{r.end_line}]"
            )
        return "\n".join(parts)


class DirCost(BaseModel):
    path: str
    tokens: int
    file_count: int


class TokenResult(BaseModel):
    files: list[FileCost]
    total_tokens: int

    @property
    def dirs(self) -> list[DirCost]:
        """Per-directory token subtotals, sorted by tokens descending."""
        from collections import defaultdict

        buckets: dict[str, int] = defaultdict(int)
        counts: dict[str, int] = defaultdict(int)
        for f in self.files:
            parent = str(Path(f.path).parent)
            buckets[parent] += f.tokens
            counts[parent] += 1
        return sorted(
            [
                DirCost(path=d, tokens=t, file_count=counts[d])
                for d, t in buckets.items()
            ],
            key=lambda x: x.tokens,
            reverse=True,
        )

    def as_text(
        self, detail: bool = False, sort: bool = False, by_dir: bool = False
    ) -> str:
        files = self.files
        if sort:
            files = sorted(files, key=lambda f: f.tokens, reverse=True)

        if by_dir:
            parts = []
            for d in self.dirs:
                parts.append(
                    f"{d.path:<50} ~{d.tokens:>6,} tokens  ({d.file_count} files)"
                )
        else:
            parts = [f.as_text(detail) for f in files]

        if len(self.files) > 1:
            parts.append("-" * 60)
            parts.append(f"{'total':<50} ~{self.total_tokens:>6,} tokens")
        return "\n".join(parts)

    def as_json(self) -> str:
        return self.model_dump_json(indent=2)


def estimate_tokens(text: str | bytes) -> int:
    if isinstance(text, bytes):
        text = text.decode(errors="replace")
    return max(1, int(len(text) / _CHARS_PER_TOKEN))


def count_file(path: Path, detail: bool = False) -> FileCost:
    try:
        display = str(path.relative_to(Path.cwd()))
    except ValueError:
        display = str(path)

    try:
        src = path.read_bytes()
    except Exception:
        return FileCost(path=display, chars=0, tokens=0, regions=[])

    chars = len(src)
    tokens = estimate_tokens(src)
    regions: list[RegionCost] = []

    if detail and path.suffix.lower() == ".py":
        regions = _py_regions(src)
    elif detail and path.suffix.lower() in {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"}:
        regions = _cpp_regions(src)

    return FileCost(path=display, chars=chars, tokens=tokens, regions=regions)


def count_paths(paths: list[Path], detail: bool = False) -> TokenResult:
    files: list[FileCost] = []
    for path in paths:
        if path.is_file():
            files.append(count_file(path, detail))
        elif path.is_dir():
            resolved_root = path.resolve()
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in _SOURCE_EXTS:
                    try:
                        rel_parts = child.resolve().relative_to(resolved_root).parts
                    except ValueError:
                        rel_parts = child.parts
                    if not any(
                        p.startswith(".") or p == "__pycache__" for p in rel_parts
                    ):
                        files.append(count_file(child, detail))
    total = sum(f.tokens for f in files)
    return TokenResult(files=files, total_tokens=total)


def _py_regions(src: bytes) -> list[RegionCost]:
    from frob.ast import python as _py
    from frob.ast.common import child_by_field, text

    try:
        _, tree = _py.parse_bytes(src)
    except Exception:
        return []

    regions: list[RegionCost] = []
    src_lines = src.decode(errors="replace").splitlines()

    for node in tree.root_node.children:
        if node.type in ("function_definition", "class_definition"):
            name_node = child_by_field(node, "name")
            name = text(name_node) if name_node else "?"
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            region_text = "\n".join(src_lines[start - 1 : end])
            regions.append(
                RegionCost(
                    name=name,
                    start_line=start,
                    end_line=end,
                    tokens=estimate_tokens(region_text),
                )
            )

    return regions


def _cpp_regions(src: bytes) -> list[RegionCost]:
    from frob.ast import cpp as _cpp
    from frob.ast.common import child_by_field, text

    try:
        _, tree = _cpp.parse_bytes(src)
    except Exception:
        return []

    regions: list[RegionCost] = []
    src_lines = src.decode(errors="replace").splitlines()

    for node in tree.root_node.named_children:
        if node.type in ("function_definition", "class_specifier", "struct_specifier"):
            name_node = child_by_field(node, "name")
            if not name_node:
                decl = child_by_field(node, "declarator")
                if decl:
                    name_node = child_by_field(decl, "declarator") or decl
            name = text(name_node) if name_node else "?"
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            region_text = "\n".join(src_lines[start - 1 : end])
            regions.append(
                RegionCost(
                    name=name,
                    start_line=start,
                    end_line=end,
                    tokens=estimate_tokens(region_text),
                )
            )

    return regions

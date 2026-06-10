from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from typani import ErrorSet, Ok, Err
from typani.result import Result

from frob.stub import stub_file, StubError
from frob.tokens import estimate_tokens


class BundleError(ErrorSet):
    TargetNotFound = "The requested target was not found in the source file"
    UnsupportedLanguage = "No bundle adapter for this file extension"
    ParseFailed = "Could not parse one or more files"


class BundleSection(BaseModel):
    path: str
    role: Literal["focus", "import"]
    content: str
    tokens: int


class Bundle(BaseModel):
    target: str
    sections: list[BundleSection]
    total_tokens: int

    def as_markdown(self) -> str:
        """
        Format the bundle for direct use as a subagent context block.
        This is the primary output format -- paste directly into a prompt.
        """
        parts: list[str] = []
        parts.append(f"# Bundle: `{self.target}`")
        parts.append(f"# Total estimated tokens: ~{self.total_tokens:,}")
        parts.append("")
        for sec in self.sections:
            role_label = "FOCUS" if sec.role == "focus" else "SIGNATURES"
            parts.append(f"## {sec.path}  [{role_label}]")
            parts.append("```")
            parts.append(sec.content.rstrip())
            parts.append("```")
            parts.append("")
        return "\n".join(parts)

    def as_text(self) -> str:
        return self.as_markdown()

    def as_json(self) -> str:
        return self.model_dump_json(indent=2)


def build_bundle(
    path: Path,
    target: str,
    depth: int = 1,
) -> Result[Bundle, BundleError]:
    """
    Build a context bundle for `target` in `path`.

    The bundle contains:
      1. `path` stubbed so only `target` has its full body (role=focus).
      2. For each local import discovered in `path`, up to `depth` levels:
         the file with ALL bodies stubbed (signatures only, role=import).
    """
    # 1. Stub the focus file
    stub_result = stub_file(path, target)
    if stub_result.is_err:
        err = stub_result.danger_err
        if err == StubError.TargetNotFound:
            return Err(BundleError.TargetNotFound)
        if err == StubError.UnsupportedLanguage:
            return Err(BundleError.UnsupportedLanguage)
        return Err(BundleError.ParseFailed)

    focus_content = stub_result.danger_ok
    sections: list[BundleSection] = [
        BundleSection(
            path=str(path),
            role="focus",
            content=focus_content,
            tokens=estimate_tokens(focus_content),
        )
    ]

    # 2. Collect local imports and produce signature-only stubs
    import_paths = _discover_local_imports(path, depth)
    for imp_path in import_paths:
        sig_content = _signatures_only(imp_path)
        if sig_content:
            sections.append(BundleSection(
                path=str(imp_path),
                role="import",
                content=sig_content,
                tokens=estimate_tokens(sig_content),
            ))

    total = sum(s.tokens for s in sections)
    return Ok(Bundle(target=target, sections=sections, total_tokens=total))


def _discover_local_imports(path: Path, depth: int) -> list[Path]:
    """Return local file paths imported by `path`, up to `depth` levels."""
    root = path.parent
    ext = path.suffix.lower()
    seen: set[str] = {str(path)}
    frontier: list[Path] = [path]
    result: list[Path] = []

    for _ in range(depth):
        next_frontier: list[Path] = []
        for p in frontier:
            imports = _get_imports_for(p, root)
            for imp in imports:
                imp_abs = (root / imp).resolve()
                key = str(imp_abs)
                if key not in seen and imp_abs.exists():
                    seen.add(key)
                    next_frontier.append(imp_abs)
                    result.append(imp_abs)
        frontier = next_frontier
        if not frontier:
            break

    return result


def _get_imports_for(path: Path, root: Path) -> list[str]:
    from frob.ast.common import ModuleTag
    ext = path.suffix.lower()
    try:
        rel = str(path.relative_to(root))
    except ValueError:
        return []

    if ext == ".py":
        from frob.ast import python as _py
        return _py.get_imports(ModuleTag(rel), root)
    elif ext in {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"}:
        from frob.ast import cpp as _cpp
        return _cpp.get_imports(ModuleTag(rel), root)
    return []


def _signatures_only(path: Path) -> str | None:
    """Return the file with ALL function/method bodies replaced by stubs."""
    ext = path.suffix.lower()
    if ext == ".py":
        return _py_signatures_only(path)
    elif ext in {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"}:
        return _cpp_signatures_only(path)
    return None


def _py_signatures_only(path: Path) -> str | None:
    from frob.ast import python as _py
    from frob.ast.common import child_by_field

    try:
        src, tree = _py.parse_file(path)
    except Exception:
        return None

    replacements: list[tuple[int, int, bytes]] = []

    def stub_body(body) -> None:
        if not body.named_children:
            return
        col = body.start_point[1]
        indent = b" " * col
        replace_start = body.start_byte - col
        replacements.append((replace_start, body.end_byte, indent + b"..."))

    def visit(node) -> None:
        if node.type == "function_definition":
            body = child_by_field(node, "body")
            if body and body.named_children:
                stub_body(body)
        for child in node.children:
            visit(child)

    visit(tree.root_node)

    result = bytearray(src)
    for start, end, replacement in sorted(replacements, key=lambda r: r[0], reverse=True):
        result[start:end] = replacement
    return result.decode()


def _cpp_signatures_only(path: Path) -> str | None:
    from frob.ast import cpp as _cpp
    from frob.ast.common import child_by_field

    try:
        src, tree = _cpp.parse_file(path)
    except Exception:
        return None

    replacements: list[tuple[int, int, bytes]] = []

    def visit(node) -> None:
        if node.type == "function_definition":
            body = child_by_field(node, "body")
            if body:
                replacements.append((body.start_byte, body.end_byte, b";"))
        for child in node.children:
            visit(child)

    visit(tree.root_node)

    result = bytearray(src)
    for start, end, replacement in sorted(replacements, key=lambda r: r[0], reverse=True):
        result[start:end] = replacement
    return result.decode()

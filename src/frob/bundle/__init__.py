from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.stub import StubError, stub_file
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
        Token count is written to stderr by the runner, not embedded here.
        """
        parts: list[str] = []
        parts.append(f"# Bundle: `{self.target}`")
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

    # Prefer a slim focus: module imports + target body only.
    # Fall back to full stub if the slim extractor fails.
    slim = _focused_content(path, target)
    focus_content = slim if slim is not None else stub_result.danger_ok
    sections: list[BundleSection] = [
        BundleSection(
            path=str(path),
            role="focus",
            content=focus_content,
            tokens=estimate_tokens(focus_content),
        )
    ]

    # 1b. Append same-file private callee signatures to the focus content
    callee_sigs = _same_file_callee_sigs(path, target)
    if callee_sigs:
        focus_content = focus_content.rstrip() + "\n\n" + callee_sigs
        sections[0] = BundleSection(
            path=sections[0].path,
            role="focus",
            content=focus_content,
            tokens=estimate_tokens(focus_content),
        )

    # 2. Collect local imports and produce signature-only stubs
    import_paths = _discover_local_imports(path, depth)
    for imp_path in import_paths:
        sig_content = _signatures_only(imp_path)
        if sig_content:
            sections.append(
                BundleSection(
                    path=str(imp_path),
                    role="import",
                    content=sig_content,
                    tokens=estimate_tokens(sig_content),
                )
            )

    total = sum(s.tokens for s in sections)
    return Ok(Bundle(target=target, sections=sections, total_tokens=total))


def _same_file_callee_sigs(path: Path, target: str) -> str:
    """
    Return signature lines for private functions in `path` that are called
    by `target`. Helps agents understand what helpers the target delegates to.
    """
    ext = path.suffix.lower()
    if ext != ".py":
        return ""

    from frob.ast import python as _py
    from frob.ast.common import child_by_field, text

    try:
        src, tree = _py.parse_file(path)
    except Exception:
        return ""

    # Find the target node
    parts = target.split(".", 1)
    class_name = parts[0] if len(parts) == 2 else None
    func_name = parts[-1]

    target_node = None
    for n in tree.root_node.children:
        if class_name and n.type == "class_definition":
            cn = child_by_field(n, "name")
            if cn and text(cn) == class_name:
                body = child_by_field(n, "body") or n
                for child in body.named_children:
                    if child.type == "function_definition":
                        fn = child_by_field(child, "name")
                        if fn and text(fn) == func_name:
                            target_node = child
                            break
        elif not class_name and n.type == "function_definition":
            fn = child_by_field(n, "name")
            if fn and text(fn) == func_name:
                target_node = n
                break

    if target_node is None:
        return ""

    # Collect all identifiers called in the target body
    called: set[str] = set()

    def collect_calls(node) -> None:
        if node.type == "call":
            fn_node = node.child_by_field_name("function")
            if fn_node:
                name = text(fn_node).split("(")[0].strip()
                if name.startswith("_"):
                    called.add(name)
        for child in node.children:
            collect_calls(child)

    collect_calls(target_node)

    if not called:
        return ""

    # Find signatures of those private functions defined at module level
    lines_out: list[str] = []
    for n in tree.root_node.children:
        if n.type == "function_definition":
            fn = child_by_field(n, "name")
            fname = text(fn) if fn else ""
            if fname in called:
                params = child_by_field(n, "parameters")
                ret = child_by_field(n, "return_type")
                sig = f"def {fname}{text(params) if params else '()'}"
                if ret:
                    sig += f" -> {text(ret)}"
                sig += ": ..."
                lines_out.append(sig)

    if not lines_out:
        return ""
    return "# same-file helpers called by target:\n" + "\n".join(lines_out)


def _focused_content(path: Path, target: str) -> str | None:
    """
    Return module-level imports + target function/class body only.

    Produces a much smaller FOCUS section than full-file stubbing for large
    files with many sibling functions. Falls back to None on parse failure.
    """
    ext = path.suffix.lower()
    if ext != ".py":
        return None  # Only implemented for Python

    from frob.ast import python as _py
    from frob.ast.common import child_by_field, text

    try:
        src, tree = _py.parse_file(path)
    except Exception:
        return None

    src_text = src.decode(errors="replace")
    lines = src_text.splitlines(keepends=True)

    parts = target.split(".", 1)
    class_name = parts[0] if len(parts) == 2 else None
    func_name = parts[-1]

    # Collect module-level import lines
    import_lines: list[str] = []
    target_lines: list[str] = []

    for node in tree.root_node.children:
        if node.type in ("import_statement", "import_from_statement"):
            start = node.start_point[0]
            end = node.end_point[0] + 1
            import_lines.extend(lines[start:end])
        elif node.type == "function_definition" and class_name is None:
            name_node = child_by_field(node, "name")
            if name_node and text(name_node) == func_name:
                start = node.start_point[0]
                end = node.end_point[0] + 1
                target_lines.extend(lines[start:end])
        elif node.type == "class_definition":
            name_node = child_by_field(node, "name")
            if name_node and text(name_node) == (class_name or ""):
                if class_name is not None:
                    # Find the specific method
                    body = child_by_field(node, "body")
                    class_start = node.start_point[0]
                    sig_end_row = body.start_point[0] if body else node.end_point[0]
                    class_sig_end = sig_end_row + 1
                    target_lines.extend(lines[class_start:class_sig_end])
                    if body:
                        for child in body.named_children:
                            if child.type == "function_definition":
                                mname = child_by_field(child, "name")
                                if mname and text(mname) == func_name:
                                    mstart = child.start_point[0]
                                    mend = child.end_point[0] + 1
                                    target_lines.extend(lines[mstart:mend])
                else:
                    # Entire class is the target
                    start = node.start_point[0]
                    end = node.end_point[0] + 1
                    target_lines.extend(lines[start:end])

    if not target_lines:
        return None

    result_parts: list[str] = []
    if import_lines:
        result_parts.append("".join(import_lines))
    result_parts.append("".join(target_lines))
    return "\n".join(result_parts)


def _discover_local_imports(path: Path, depth: int) -> list[Path]:
    """Return local file paths imported by `path`, up to `depth` levels."""
    root = path.parent
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

    try:
        rel = str(path.relative_to(root))
    except ValueError:
        return []

    ext = path.suffix.lower()
    if ext == ".py":
        from frob.ast import python as _py

        return [str(t) for t in _py.get_imports(ModuleTag(rel), root)]
    elif ext in {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hxx"}:
        from frob.ast import cpp as _cpp

        return [str(t) for t in _cpp.get_imports(ModuleTag(rel), root)]
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
    for start, end, replacement in sorted(
        replacements, key=lambda r: r[0], reverse=True
    ):
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
    for start, end, replacement in sorted(
        replacements, key=lambda r: r[0], reverse=True
    ):
        result[start:end] = replacement
    return result.decode()

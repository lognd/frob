from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result


class OutlineError(ErrorSet):
    UnsupportedLanguage = "No outline adapter for this file extension"
    ParseFailed = "tree-sitter could not parse the file"


class FunctionOutline(BaseModel):
    name: str
    signature: str
    line: int
    doc: str = ""


class ClassOutline(BaseModel):
    name: str
    line: int
    methods: list[FunctionOutline]


class ModuleOutline(BaseModel):
    path: str
    lines: int
    imports: list[str]
    functions: list[FunctionOutline]
    classes: list[ClassOutline]

    def as_text(self, include_private: bool = False) -> str:
        parts = [f"{self.path}  ({self.lines} lines)"]
        if self.imports:
            parts.append(f"  imports: {', '.join(self.imports)}")

        hidden_fns = 0
        for fn in self.functions:
            if not include_private and fn.name.startswith("_"):
                hidden_fns += 1
                continue
            line = f"  {fn.signature}  [L{fn.line}]"
            if fn.doc:
                line += f"  -- {fn.doc}"
            parts.append(line)

        hidden_methods = 0
        for cls in self.classes:
            if not include_private and cls.name.startswith("_"):
                hidden_fns += 1
                continue
            parts.append(f"  class {cls.name}  [L{cls.line}]")
            for m in cls.methods:
                if not include_private and m.name.startswith("_"):
                    hidden_methods += 1
                    continue
                line = f"    {m.signature}  [L{m.line}]"
                if m.doc:
                    line += f"  -- {m.doc}"
                parts.append(line)

        total_hidden = hidden_fns + hidden_methods
        if total_hidden > 0:
            parts.append(f"  [{total_hidden} private -- use --all to show]")

        return "\n".join(parts)

    def as_json(self) -> str:
        return self.model_dump_json(indent=2)


_PY_EXTS = {".py"}


def outline_file(path: Path) -> Result[ModuleOutline, OutlineError]:
    try:
        display = path.relative_to(Path.cwd())
    except ValueError:
        display = path

    ext = path.suffix.lower()
    if ext in _PY_EXTS:
        result = _outline_python(path)
    else:
        from frob.ast.cpp import ALL_EXTS as _CPP_EXTS

        if ext in _CPP_EXTS:
            result = _outline_cpp(path)
        else:
            return Err(OutlineError.UnsupportedLanguage)

    if result.is_ok:
        result.danger_ok.path = str(display)
    return result


def _outline_python(path: Path) -> Result[ModuleOutline, OutlineError]:
    from frob.ast import python as _py
    from frob.ast.common import child_by_field, text

    try:
        src, tree = _py.parse_file(path)
    except Exception:
        return Err(OutlineError.ParseFailed)

    lines = src.count(b"\n") + 1
    imports: list[str] = []
    functions: list[FunctionOutline] = []
    classes: list[ClassOutline] = []

    for node in tree.root_node.children:
        if node.type == "import_statement":
            for child in node.named_children:
                name = text(child).split(".")[0]
                if name not in imports:
                    imports.append(name)
        elif node.type == "import_from_statement":
            mod = child_by_field(node, "module_name")
            if mod:
                name = text(mod).split(".")[0]
                if name not in imports:
                    imports.append(name)
        elif node.type == "function_definition":
            fn = _py_function_outline(node)
            if fn:
                functions.append(fn)
        elif node.type == "class_definition":
            cls = _py_class_outline(node)
            if cls:
                classes.append(cls)

    return Ok(
        ModuleOutline(
            path=str(path),
            lines=lines,
            imports=imports,
            functions=functions,
            classes=classes,
        )
    )


def _py_function_outline(node) -> FunctionOutline | None:
    from frob.ast.common import child_by_field, text

    name_node = child_by_field(node, "name")
    if name_node is None:
        return None
    name = text(name_node)
    sig = _py_signature(node)
    doc = _py_first_doc_line(node)
    return FunctionOutline(
        name=name, signature=sig, line=node.start_point[0] + 1, doc=doc
    )


def _py_first_doc_line(node) -> str:
    """Extract first non-blank sentence from docstring, if present."""
    body = None
    for child in node.children:
        if child.type == "block":
            body = child
            break
    if body is None:
        return ""
    for child in body.named_children:
        if child.type == "expression_statement":
            for sub in child.named_children:
                if sub.type == "string":
                    raw = sub.text.decode(errors="replace") if sub.text else ""
                    # Strip quotes
                    for q in ('"""', "'''", '"', "'"):
                        if raw.startswith(q):
                            raw = raw[len(q) :]
                            if raw.endswith(q):
                                raw = raw[: -len(q)]
                            break
                    # First non-blank line, truncated at sentence end or 80 chars
                    for ln in raw.splitlines():
                        ln = ln.strip()
                        if ln:
                            idx = ln.find(".")
                            if 0 < idx < 80:
                                return ln[: idx + 1]
                            return ln[:80]
            break
    return ""


def _py_signature(node) -> str:
    """Reconstruct a clean function signature from a tree-sitter node."""
    from frob.ast.common import child_by_field, text

    name_node = child_by_field(node, "name")
    params_node = child_by_field(node, "parameters")
    ret_node = child_by_field(node, "return_type")

    name = text(name_node) if name_node else "?"
    params = text(params_node) if params_node else "()"
    ret = f" -> {text(ret_node)}" if ret_node else ""
    return f"{name}{params}{ret}"


def _py_class_outline(node) -> ClassOutline | None:
    from frob.ast.common import child_by_field, text

    name_node = child_by_field(node, "name")
    if name_node is None:
        return None
    name = text(name_node)
    line = node.start_point[0] + 1
    methods: list[FunctionOutline] = []
    body = child_by_field(node, "body")
    if body:
        for child in body.named_children:
            if child.type == "function_definition":
                fn = _py_function_outline(child)
                if fn:
                    methods.append(fn)
    return ClassOutline(name=name, line=line, methods=methods)


def _outline_cpp(path: Path) -> Result[ModuleOutline, OutlineError]:
    from frob.ast import cpp as _cpp
    from frob.ast.common import child_by_field, text  # noqa: F401

    try:
        src, tree = _cpp.parse_file(path)
    except Exception:
        return Err(OutlineError.ParseFailed)

    lines = src.count(b"\n") + 1
    imports: list[str] = []
    functions: list[FunctionOutline] = []
    classes: list[ClassOutline] = []

    for node in tree.root_node.named_children:
        if node.type == "preproc_include":
            path_node = node.named_children[0] if node.named_children else None
            if path_node:
                raw = text(path_node).strip('"<>')
                if raw not in imports:
                    imports.append(raw)
        elif node.type == "function_definition":
            fn = _cpp_function_outline(node)
            if fn:
                functions.append(fn)
        elif node.type in ("class_specifier", "struct_specifier"):
            cls = _cpp_class_outline(node)
            if cls:
                classes.append(cls)

    return Ok(
        ModuleOutline(
            path=str(path),
            lines=lines,
            imports=imports,
            functions=functions,
            classes=classes,
        )
    )


def _cpp_function_outline(node) -> FunctionOutline | None:
    from frob.ast.common import child_by_field, text

    decl = child_by_field(node, "declarator")
    if decl is None:
        return None
    name_node = child_by_field(decl, "declarator")
    name = text(name_node) if name_node else text(decl)
    # Reconstruct signature: return_type + declarator (minus body)
    body = child_by_field(node, "body")
    if body:
        sig = text(node).replace(text(body), "").strip().rstrip("{").strip()
    else:
        sig = text(node).rstrip(";").strip()
    return FunctionOutline(name=name, signature=sig, line=node.start_point[0] + 1)


def _cpp_class_outline(node) -> ClassOutline | None:
    from frob.ast.common import child_by_field, text

    name_node = child_by_field(node, "name")
    if name_node is None:
        return None
    name = text(name_node)
    line = node.start_point[0] + 1
    methods: list[FunctionOutline] = []
    body = child_by_field(node, "body")
    if body:
        for child in body.named_children:
            if child.type == "function_definition":
                fn = _cpp_function_outline(child)
                if fn:
                    methods.append(fn)
    return ClassOutline(name=name, line=line, methods=methods)

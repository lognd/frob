from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from typani import ErrorSet, Ok, Err
from typani.result import Result


class XrefError(ErrorSet):
    NoFilesFound = "No source files found under the given path"


class Definition(BaseModel):
    file: str
    line: int


class Usage(BaseModel):
    file: str
    line: int
    context: str


class XrefResult(BaseModel):
    symbol: str
    definition: Definition | None
    usages: list[Usage]

    def as_text(self) -> str:
        parts = [self.symbol]
        if self.definition:
            parts.append(f"  defined:  {self.definition.file}:{self.definition.line}")
        else:
            parts.append("  defined:  (not found)")
        if self.usages:
            parts.append("  used by:")
            for u in self.usages:
                parts.append(f"    {u.file}:{u.line:<6} {u.context.strip()}")
        else:
            parts.append("  used by: (none found)")
        return "\n".join(parts)

    def as_json(self) -> str:
        return self.model_dump_json(indent=2)


_PY_EXTS = {".py"}
_CPP_EXTS = {".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hpp", ".hxx", ".h++"}
_SOURCE_EXTS = _PY_EXTS | _CPP_EXTS


def xref(
    symbol: str,
    root: Path,
    lang: str | None = None,
) -> Result[XrefResult, XrefError]:
    files = _collect_source_files(root, lang)
    if not files:
        return Err(XrefError.NoFilesFound)

    definition: Definition | None = None
    usages: list[Usage] = []

    for path in files:
        ext = path.suffix.lower()
        try:
            rel = str(path.relative_to(root)) if root.is_dir() else path.name
        except ValueError:
            rel = str(path)

        src = path.read_bytes()
        src_lines = src.decode(errors="replace").splitlines()

        if ext in _PY_EXTS:
            defn, file_usages = _search_python(src, src_lines, symbol, rel)
        elif ext in _CPP_EXTS:
            defn, file_usages = _search_cpp(src, src_lines, symbol, rel)
        else:
            defn, file_usages = _search_text(src_lines, symbol, rel)

        if defn and definition is None:
            definition = defn
        usages.extend(file_usages)

    return Ok(XrefResult(symbol=symbol, definition=definition, usages=usages))


def _collect_source_files(root: Path, lang: str | None) -> list[Path]:
    if lang == "python":
        exts = _PY_EXTS
    elif lang in ("cpp", "c"):
        exts = _CPP_EXTS
    else:
        exts = _SOURCE_EXTS

    if root.is_file():
        return [root] if root.suffix.lower() in exts else []

    results: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in exts:
            if not any(p.startswith(".") or p == "__pycache__"
                       for p in path.parts):
                results.append(path)
    return results


def _search_python(
    src: bytes, src_lines: list[str], symbol: str, rel: str
) -> tuple[Definition | None, list[Usage]]:
    from frob.ast import python as _py
    from tree_sitter import Node

    _, tree = _py.parse_bytes(src)
    definition: Definition | None = None
    usages: list[Usage] = []

    def visit(node: Node) -> None:
        nonlocal definition

        # Definition: function_definition or class_definition with matching name
        if node.type in ("function_definition", "class_definition"):
            name_node = node.child_by_field_name("name")
            if name_node and name_node.text and name_node.text.decode() == symbol:
                line = node.start_point[0] + 1
                if definition is None:
                    definition = Definition(file=rel, line=line)

        # Usage: any identifier that matches and is NOT the definition name
        elif node.type == "identifier":
            if node.text and node.text.decode() == symbol:
                parent = node.parent
                # Skip if this node IS the name field of a definition
                if parent and parent.type in ("function_definition", "class_definition"):
                    if parent.child_by_field_name("name") is node:
                        for child in node.children:
                            visit(child)
                        return
                line = node.start_point[0] + 1
                ctx = src_lines[line - 1] if line <= len(src_lines) else ""
                usages.append(Usage(file=rel, line=line, context=ctx))

        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return definition, usages


def _search_cpp(
    src: bytes, src_lines: list[str], symbol: str, rel: str
) -> tuple[Definition | None, list[Usage]]:
    from frob.ast import cpp as _cpp
    from tree_sitter import Node

    _, tree = _cpp.parse_bytes(src)
    definition: Definition | None = None
    usages: list[Usage] = []

    def visit(node: Node) -> None:
        nonlocal definition

        if node.type == "function_definition":
            decl = node.child_by_field_name("declarator")
            if decl:
                inner = decl.child_by_field_name("declarator")
                name_node = inner or decl
                if name_node.text and name_node.text.decode() == symbol:
                    line = node.start_point[0] + 1
                    if definition is None:
                        definition = Definition(file=rel, line=line)

        elif node.type in ("class_specifier", "struct_specifier"):
            name_node = node.child_by_field_name("name")
            if name_node and name_node.text and name_node.text.decode() == symbol:
                line = node.start_point[0] + 1
                if definition is None:
                    definition = Definition(file=rel, line=line)

        elif node.type in ("identifier", "type_identifier"):
            if node.text and node.text.decode() == symbol:
                line = node.start_point[0] + 1
                ctx = src_lines[line - 1] if line <= len(src_lines) else ""
                usages.append(Usage(file=rel, line=line, context=ctx))

        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return definition, usages


def _search_text(
    src_lines: list[str], symbol: str, rel: str
) -> tuple[Definition | None, list[Usage]]:
    usages: list[Usage] = []
    for i, line in enumerate(src_lines, 1):
        if symbol in line:
            usages.append(Usage(file=rel, line=i, context=line))
    return None, usages

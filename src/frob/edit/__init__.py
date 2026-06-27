from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.ast import python as _py
from frob.ast.common import child_by_field
from frob.ast.common import text as ast_text


class EditError(ErrorSet):
    UnsupportedFile = "Only Python files are supported"
    ParseFailed = "Could not parse the file"
    SymbolNotFound = "Symbol not found in file"
    AmbiguousSymbol = "Multiple symbols match; use ClassName.method to disambiguate"


class IsolatedSymbol(BaseModel):
    path: str
    symbol: str
    start_line: int
    end_line: int
    source: str


def isolate(path: Path, symbol: str) -> Result[IsolatedSymbol, EditError]:
    if path.suffix.lower() != ".py":
        return Err(EditError.UnsupportedFile)
    try:
        src_bytes, tree = _py.parse_file(path)
    except Exception:
        return Err(EditError.ParseFailed)

    src_text = src_bytes.decode("utf-8", errors="replace")
    lines = src_text.splitlines(keepends=True)

    parts = symbol.split(".", 1)
    if len(parts) == 2:
        class_name, method_name = parts
        return _find_method(tree, lines, path, symbol, class_name, method_name)
    else:
        return _find_top_level(tree, lines, path, symbol)


def replace(path: Path, symbol: str, new_source: str) -> Result[None, EditError]:
    result = isolate(path, symbol)
    if result.is_err:
        return Err(result.danger_err)
    iso = result.danger_ok

    src = path.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)

    before = lines[: iso.start_line - 1]
    after = lines[iso.end_line :]

    new_lines = new_source.splitlines(keepends=True)
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    path.write_text("".join(before + new_lines + after), encoding="utf-8")
    return Ok(None)


def _find_top_level(tree, lines, path, symbol):
    matches = []
    for node in tree.root_node.children:
        if node.type in ("function_definition", "class_definition", "decorated_definition"):
            name_node = _get_name(node)
            if name_node and ast_text(name_node) == symbol:
                matches.append(node)
    if not matches:
        return Err(EditError.SymbolNotFound)
    if len(matches) > 1:
        return Err(EditError.AmbiguousSymbol)
    node = matches[0]
    start = node.start_point[0]
    end = node.end_point[0]
    source = "".join(lines[start : end + 1])
    return Ok(IsolatedSymbol(
        path=str(path),
        symbol=symbol,
        start_line=start + 1,
        end_line=end + 1,
        source=source,
    ))


def _find_method(tree, lines, path, full_symbol, class_name, method_name):
    for node in tree.root_node.children:
        if node.type == "class_definition":
            name_node = child_by_field(node, "name")
            if name_node and ast_text(name_node) == class_name:
                body = child_by_field(node, "body")
                if body:
                    for child in body.named_children:
                        if child.type == "function_definition":
                            mn = child_by_field(child, "name")
                            if mn and ast_text(mn) == method_name:
                                start = child.start_point[0]
                                end = child.end_point[0]
                                source = "".join(lines[start : end + 1])
                                return Ok(IsolatedSymbol(
                                    path=str(path),
                                    symbol=full_symbol,
                                    start_line=start + 1,
                                    end_line=end + 1,
                                    source=source,
                                ))
    return Err(EditError.SymbolNotFound)


def _get_name(node):
    if node.type == "decorated_definition":
        for child in node.named_children:
            if child.type in ("function_definition", "class_definition"):
                return child_by_field(child, "name")
        return None
    return child_by_field(node, "name")

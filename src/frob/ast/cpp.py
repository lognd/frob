from __future__ import annotations

from pathlib import Path

import tree_sitter_cpp as _tscpp
from tree_sitter import Language, Node, Tree

from frob.ast.common import (
    ClassTag,
    FunctionTag,
    ModuleTag,
    child_by_field,
    make_parser,
    text,
)

_LANGUAGE = Language(_tscpp.language())
_PARSER = make_parser(_LANGUAGE)

_HEADER_EXTS = {".h", ".hpp", ".hxx", ".h++"}
_SOURCE_EXTS = {".c", ".cc", ".cpp", ".cxx", ".c++"}
ALL_EXTS = _HEADER_EXTS | _SOURCE_EXTS


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_file(path: Path) -> tuple[bytes, Tree]:
    src = path.read_bytes()
    return src, _PARSER.parse(src)


def parse_bytes(src: bytes) -> tuple[bytes, Tree]:
    return src, _PARSER.parse(src)


# ---------------------------------------------------------------------------
# UsableByCycle
# ---------------------------------------------------------------------------


def get_imports(mod_tag: ModuleTag, root: Path) -> list[ModuleTag]:
    path = root / mod_tag
    _, tree = parse_file(path)
    return _extract_includes(tree.root_node, path.parent, root)


def _extract_includes(node: Node, file_dir: Path, root: Path) -> list[ModuleTag]:
    results: list[ModuleTag] = []

    def visit(n: Node) -> None:
        if n.type == "preproc_include":
            path_node = n.named_children[0] if n.named_children else None
            if path_node is None:
                return
            raw = text(path_node).strip('"<>')
            # Only track local includes (quoted), not system includes (<...>)
            if path_node.type == "string_literal":
                candidate = (file_dir / raw).resolve()
                try:
                    rel = candidate.relative_to(root.resolve())
                    if candidate.exists():
                        results.append(ModuleTag(str(rel)))
                except ValueError:
                    pass
        for child in n.children:
            visit(child)

    visit(node)
    return results


# ---------------------------------------------------------------------------
# UsableByStub
# ---------------------------------------------------------------------------


def _iter_function_nodes(parent: Node):
    """Yield (node, qualified_name) for all function definitions under parent."""
    for n in parent.named_children:
        if n.type in ("function_definition", "declaration"):
            decl = child_by_field(n, "declarator")
            if decl:
                yield n, _declarator_name(decl)
        elif n.type in ("class_specifier", "struct_specifier"):
            class_name = text(child_by_field(n, "name") or n)
            body = child_by_field(n, "body")
            if body:
                for m in body.named_children:
                    if m.type in ("function_definition", "declaration"):
                        decl = child_by_field(m, "declarator")
                        if decl:
                            yield m, f"{class_name}::{_declarator_name(decl)}"


def _declarator_name(node: Node) -> str:
    if node.type == "function_declarator":
        name_node = child_by_field(node, "declarator")
        return text(name_node) if name_node else text(node)
    return text(node)


def get_classes(tree: Tree) -> list[ClassTag]:
    return [
        ClassTag(text(child_by_field(n, "name") or n))
        for n in tree.root_node.named_children
        if n.type in ("class_specifier", "struct_specifier")
    ]


def get_all_functions(tree: Tree) -> list[FunctionTag]:
    return [FunctionTag(name) for _, name in _iter_function_nodes(tree.root_node)]


def get_class_functions(class_node: Node) -> list[FunctionTag]:
    body = child_by_field(class_node, "body")
    if body is None:
        return []
    return [
        FunctionTag(_declarator_name(child_by_field(n, "declarator") or n))
        for n in body.named_children
        if n.type in ("function_definition", "declaration")
    ]


# ---------------------------------------------------------------------------
# StubEmitter
# ---------------------------------------------------------------------------


def emit_stub(source: bytes, tree: Tree, target: str) -> str:
    """
    Replace every non-target function body with `;` (forward declaration).
    target format: "func_name" or "ClassName::method_name"
    """
    replacements: list[tuple[int, int, bytes]] = []

    for n, name in _iter_function_nodes(tree.root_node):
        if name == target:
            continue
        if n.type == "function_definition":
            body = child_by_field(n, "body")
            if body:
                # Replace body with `;` to produce a declaration
                replacements.append((body.start_byte, body.end_byte, b";"))

    result = bytearray(source)
    for start, end, replacement in sorted(
        replacements, key=lambda r: r[0], reverse=True
    ):
        result[start:end] = replacement

    return result.decode()

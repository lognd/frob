from __future__ import annotations

from pathlib import Path

import tree_sitter_python as _tsp
from tree_sitter import Language, Node, Tree

from frob.ast.common import (
    ClassTag,
    FunctionTag,
    ModuleTag,
    make_parser,
    text,
    child_by_field,
)

_LANGUAGE = Language(_tsp.language())
_PARSER = make_parser(_LANGUAGE)


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
    """
    Parse the file at mod_tag (relative to root) and return all local imports
    as ModuleTags (relative paths that exist under root).
    """
    path = root / mod_tag
    _, tree = parse_file(path)
    return _extract_imports(tree.root_node, mod_tag, root)


def _extract_imports(node: Node, origin: ModuleTag, root: Path) -> list[ModuleTag]:
    results: list[ModuleTag] = []

    def visit(n: Node) -> None:
        if n.type == "import_statement":
            for name_node in n.named_children:
                _resolve_dotted(name_node, root, results)
        elif n.type == "import_from_statement":
            mod_node = child_by_field(n, "module_name")
            if mod_node:
                _resolve_dotted(mod_node, root, results)
        for child in n.children:
            visit(child)

    visit(node)
    return results


def _resolve_dotted(node: Node, root: Path, out: list[ModuleTag]) -> None:
    name = text(node).replace(".", "/")
    for suffix in (".py", "/__init__.py"):
        candidate = Path(name + suffix)
        if (root / candidate).exists():
            out.append(ModuleTag(str(candidate)))
            return


# ---------------------------------------------------------------------------
# UsableByStub
# ---------------------------------------------------------------------------


def get_classes(tree: Tree) -> list[ClassTag]:
    return [
        ClassTag(text(child_by_field(n, "name") or n))
        for n in tree.root_node.children
        if n.type == "class_definition"
    ]


def get_all_functions(tree: Tree) -> list[FunctionTag]:
    return [
        FunctionTag(text(child_by_field(n, "name") or n))
        for n in tree.root_node.children
        if n.type == "function_definition"
    ]


def get_class_functions(class_node: Node) -> list[FunctionTag]:
    body = child_by_field(class_node, "body")
    if body is None:
        return []
    return [
        FunctionTag(text(child_by_field(n, "name") or n))
        for n in body.named_children
        if n.type == "function_definition"
    ]


def find_class_node(tree: Tree, class_name: str) -> Node | None:
    for n in tree.root_node.children:
        if n.type == "class_definition":
            name_node = child_by_field(n, "name")
            if name_node and text(name_node) == class_name:
                return n
    return None


def find_function_node(parent: Node, func_name: str) -> Node | None:
    body_node = child_by_field(parent, "body") or parent
    for n in body_node.named_children:
        if n.type == "function_definition":
            name_node = child_by_field(n, "name")
            if name_node and text(name_node) == func_name:
                return n
    return None


# ---------------------------------------------------------------------------
# StubEmitter
# ---------------------------------------------------------------------------


def emit_stub(source: bytes, tree: Tree, target: str) -> str:
    """
    Return source with every function/method body except target replaced by
    a single `...` expression, preserving signatures and decorators.

    target format: "func_name" or "ClassName.method_name"
    """
    parts = target.split(".", 1)
    class_name = parts[0] if len(parts) == 2 else None
    func_name = parts[-1]

    replacements: list[tuple[int, int, bytes]] = []

    def stub_body(body: Node) -> None:
        if not body.named_children:
            return
        col = body.start_point[1]
        indent = b" " * col
        # body.start_byte is after the leading whitespace; step back to consume it
        replace_start = body.start_byte - col
        replacements.append((replace_start, body.end_byte, indent + b"..."))

    def visit_functions(parent: Node, in_target_class: bool) -> None:
        body_node = child_by_field(parent, "body") or parent
        for n in body_node.named_children:
            if n.type != "function_definition":
                continue
            name_node = child_by_field(n, "name")
            name = text(name_node) if name_node else ""
            is_target = (
                (class_name is None and name == func_name)
                or (in_target_class and name == func_name)
            )
            if not is_target:
                body = child_by_field(n, "body")
                if body and body.named_children:
                    stub_body(body)

    for n in tree.root_node.children:
        if n.type == "class_definition":
            name_node = child_by_field(n, "name")
            is_target_class = class_name is not None and text(name_node) == class_name
            if not is_target_class and class_name is None:
                visit_functions(n, False)
            else:
                visit_functions(n, is_target_class)
        elif n.type == "function_definition":
            name_node = child_by_field(n, "name")
            is_target = class_name is None and text(name_node) == func_name
            if not is_target:
                body = child_by_field(n, "body")
                if body and body.named_children:
                    stub_body(body)

    # Apply replacements in reverse order so offsets stay valid
    result = bytearray(source)
    for start, end, replacement in sorted(replacements, key=lambda r: r[0], reverse=True):
        result[start:end] = replacement

    return result.decode()

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel

from frob.logging import get_logger

_log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ArchCategory = Literal[
    "long-function",
    "god-class",
    "high-coupling",
    "deep-nesting",
    "abstraction-opportunity",
    "large-file",
]

ArchSeverity = Literal["warning", "suggestion", "info"]

_SKIP_DIRS = {"__pycache__", ".venv", "build", "dist"}


def _is_skip_dir(name: str) -> bool:
    return name in _SKIP_DIRS or name.endswith(".egg-info")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ArchSuggestion(BaseModel):
    file: str
    line: int | None = None
    category: ArchCategory
    severity: ArchSeverity
    message: str
    detail: str | None = None


class ArchResult(BaseModel):
    root: str
    suggestions: list[ArchSuggestion]

    def as_text(self) -> str:
        if not self.suggestions:
            return "no architectural issues found"
        lines: list[str] = []
        for s in self.suggestions:
            loc = s.file
            if s.line is not None:
                loc = f"{loc}:{s.line}"
            lines.append(f"{loc}  {s.severity}  {s.category}")
            lines.append(f"  {s.message}")
            if s.detail:
                lines.append(f"  {s.detail}")
        return "\n".join(lines)

    def as_json(self) -> str:
        return json.dumps(self.model_dump(), indent=2)


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------


def _collect_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for p in root.rglob("*"):
        # Check all parent parts relative to root for skip dirs
        try:
            rel_parts = p.relative_to(root).parts
        except ValueError:
            continue
        if any(_is_skip_dir(part) for part in rel_parts):
            continue
        if p.is_file():
            result.append(p)
    return result


# ---------------------------------------------------------------------------
# Large-file check
# ---------------------------------------------------------------------------


def _check_large_file(
    path: Path,
    rel: str,
    lines: list[bytes],
    max_file_lines: int,
    out: list[ArchSuggestion],
) -> None:
    n = len(lines)
    if n > max_file_lines:
        out.append(
            ArchSuggestion(
                file=rel,
                category="large-file",
                severity="info",
                message=f"file has {n} lines (threshold: {max_file_lines})",
            )
        )


# ---------------------------------------------------------------------------
# Python checks
# ---------------------------------------------------------------------------


def _py_function_line_count(func_node: "object") -> int:
    from tree_sitter import Node

    n: Node = cast("Node", func_node)
    body = n.child_by_field_name("body")
    if body is None:
        return 0
    return body.end_point[0] - body.start_point[0] + 1


def _py_check_long_functions(
    tree: "object",
    rel: str,
    max_function_lines: int,
    out: list[ArchSuggestion],
) -> None:
    from tree_sitter import Node, Tree

    from frob.ast.common import child_by_field, text

    t: Tree = cast("Tree", tree)

    def visit(node: Node, class_prefix: str) -> None:
        for child in node.children:
            if child.type == "class_definition":
                name_node = child_by_field(child, "name")
                cname = text(name_node) if name_node else "?"
                body = child_by_field(child, "body")
                if body:
                    visit(body, cname + ".")
            elif child.type == "function_definition":
                name_node = child_by_field(child, "name")
                fname = text(name_node) if name_node else "?"
                n_lines = _py_function_line_count(child)
                if n_lines > max_function_lines:
                    start_line = child.start_point[0] + 1
                    out.append(
                        ArchSuggestion(
                            file=rel,
                            line=start_line,
                            category="long-function",
                            severity="warning",
                            message=(
                                f"function `{class_prefix}{fname}` has"
                                f" {n_lines} lines (threshold: {max_function_lines})"
                            ),
                        )
                    )
                # recurse for nested functions
                body = child_by_field(child, "body")
                if body:
                    visit(body, class_prefix)

    visit(t.root_node, "")


def _py_check_god_classes(
    tree: "object",
    rel: str,
    max_class_methods: int,
    out: list[ArchSuggestion],
) -> None:
    from tree_sitter import Tree

    from frob.ast.common import child_by_field, text

    t: Tree = cast("Tree", tree)

    for child in t.root_node.children:
        if child.type != "class_definition":
            continue
        name_node = child_by_field(child, "name")
        cname = text(name_node) if name_node else "?"
        body = child_by_field(child, "body")
        if body is None:
            continue
        methods = [n for n in body.named_children if n.type == "function_definition"]
        n_methods = len(methods)
        if n_methods > max_class_methods:
            start_line = child.start_point[0] + 1
            out.append(
                ArchSuggestion(
                    file=rel,
                    line=start_line,
                    category="god-class",
                    severity="warning",
                    message=f"class `{cname}` has {n_methods} methods"
                    f" (threshold: {max_class_methods})",
                )
            )


def _py_check_high_coupling(
    tree: "object",
    rel: str,
    root: Path,
    max_local_imports: int,
    out: list[ArchSuggestion],
) -> None:
    from frob.ast import python as _py
    from frob.ast.common import ModuleTag

    mod_tag = ModuleTag(rel)
    try:
        imports = _py.get_imports(mod_tag, root)
    except Exception as exc:
        _log.debug("high-coupling: failed to parse %s: %s", rel, exc)
        return
    n = len(set(imports))
    if n > max_local_imports:
        out.append(
            ArchSuggestion(
                file=rel,
                category="high-coupling",
                severity="suggestion",
                message=f"file imports {n} local modules (threshold: {max_local_imports})",  # noqa: E501
            )
        )


def _py_max_nesting(func_body_node: "object") -> int:
    from tree_sitter import Node

    body: Node = cast("Node", func_body_node)

    _NESTING_TYPES = {
        "if_statement",
        "for_statement",
        "while_statement",
        "try_statement",
        "with_statement",
    }

    def depth(node: Node, current: int) -> int:
        best = current
        for child in node.children:
            if child.type in _NESTING_TYPES:
                d = depth(child, current + 1)
            else:
                d = depth(child, current)
            if d > best:
                best = d
        return best

    return depth(body, 0)


def _py_check_deep_nesting(
    tree: "object",
    rel: str,
    max_nesting_depth: int,
    out: list[ArchSuggestion],
) -> None:
    from tree_sitter import Node, Tree

    from frob.ast.common import child_by_field, text

    t: Tree = cast("Tree", tree)

    def visit_functions(node: Node, class_prefix: str) -> None:
        for child in node.children:
            if child.type == "class_definition":
                name_node = child_by_field(child, "name")
                cname = text(name_node) if name_node else "?"
                body = child_by_field(child, "body")
                if body:
                    visit_functions(body, cname + ".")
            elif child.type == "function_definition":
                name_node = child_by_field(child, "name")
                fname = text(name_node) if name_node else "?"
                body = child_by_field(child, "body")
                if body:
                    depth = _py_max_nesting(body)
                    if depth > max_nesting_depth:
                        start_line = child.start_point[0] + 1
                        out.append(
                            ArchSuggestion(
                                file=rel,
                                line=start_line,
                                category="deep-nesting",
                                severity="suggestion",
                                message=(
                                    f"function `{class_prefix}{fname}` has"
                                    f" nesting depth {depth}"
                                    f" (threshold: {max_nesting_depth})"
                                ),
                            )
                        )
                    # recurse for nested functions
                    visit_functions(body, class_prefix)

    visit_functions(t.root_node, "")


# ---------------------------------------------------------------------------
# Abstraction-opportunity check (cross-file)
# ---------------------------------------------------------------------------


def _annotation_text(node: "object") -> str:
    from tree_sitter import Node

    from frob.ast.common import text

    n: Node = cast("Node", node)
    return text(n).strip()


def _extract_py_signatures(
    tree: "object",
    rel: str,
) -> list[tuple[str, str, tuple[str, ...], str]]:
    """
    Return list of (rel, func_name, param_types_tuple, return_type_str).
    Only includes functions that have at least one annotated parameter or return.
    """
    from tree_sitter import Node, Tree

    from frob.ast.common import child_by_field, text

    t: Tree = cast("Tree", tree)
    results = []

    def visit(node: Node) -> None:
        for child in node.children:
            if child.type in ("class_definition",):
                body = child_by_field(child, "body")
                if body:
                    visit(body)
            elif child.type == "function_definition":
                name_node = child_by_field(child, "name")
                fname = text(name_node) if name_node else "?"

                # parameters
                params_node = child_by_field(child, "parameters")
                param_types: list[str] = []
                if params_node:
                    for p in params_node.named_children:
                        if p.type in ("typed_parameter", "typed_default_parameter"):
                            ann = child_by_field(p, "type")
                            if ann:
                                param_types.append(_annotation_text(ann))
                        elif p.type == "identifier":
                            # unannotated param -- skip
                            pass

                # return type
                ret_node = child_by_field(child, "return_type")
                ret = _annotation_text(ret_node) if ret_node else ""

                if param_types or ret:
                    results.append((rel, fname, tuple(param_types), ret))

                # recurse for nested functions
                body = child_by_field(child, "body")
                if body:
                    visit(body)

    visit(t.root_node)
    return results


def _check_abstraction_opportunities(
    all_sigs: list[tuple[str, str, tuple[str, ...], str]],
    out: list[ArchSuggestion],
) -> None:
    # group by (param_types_tuple, return_type)
    # only non-trivial: param_types must be non-empty
    groups: dict[tuple[tuple[str, ...], str], list[tuple[str, str]]] = defaultdict(list)
    for rel, fname, ptypes, ret in all_sigs:
        if not ptypes:
            continue
        key = (ptypes, ret)
        groups[key].append((rel, fname))

    for (ptypes, ret), members in groups.items():
        if len(members) < 3:
            continue
        params_str = ", ".join(ptypes)
        sig_str = f"({params_str}) -> {ret}" if ret else f"({params_str})"
        fn_names = ", ".join(fname for _, fname in members)
        # Use the first file as the location (arbitrary but stable)
        first_file = members[0][0]
        out.append(
            ArchSuggestion(
                file=first_file,
                category="abstraction-opportunity",
                severity="suggestion",
                message=(
                    f"{len(members)} functions share signature `{sig_str}`: {fn_names}"
                ),
                detail="Consider a shared protocol or base class",
            )
        )


# ---------------------------------------------------------------------------
# C++ checks
# ---------------------------------------------------------------------------


def _cpp_check_long_functions(
    tree: "object",
    rel: str,
    max_function_lines: int,
    out: list[ArchSuggestion],
) -> None:
    from tree_sitter import Tree

    from frob.ast.common import child_by_field
    from frob.ast.cpp import _iter_function_nodes

    t: Tree = cast("Tree", tree)

    for node, name in _iter_function_nodes(t.root_node):
        if node.type != "function_definition":
            continue
        body = child_by_field(node, "body")
        if body is None:
            continue
        n_lines = body.end_point[0] - body.start_point[0] + 1
        if n_lines > max_function_lines:
            start_line = node.start_point[0] + 1
            out.append(
                ArchSuggestion(
                    file=rel,
                    line=start_line,
                    category="long-function",
                    severity="warning",
                    message=f"function `{name}` has {n_lines} lines"
                    f" (threshold: {max_function_lines})",
                )
            )


def _cpp_check_god_classes(
    tree: "object",
    rel: str,
    max_class_methods: int,
    out: list[ArchSuggestion],
) -> None:
    from tree_sitter import Tree

    from frob.ast.common import child_by_field, text

    t: Tree = cast("Tree", tree)

    for child in t.root_node.named_children:
        if child.type not in ("class_specifier", "struct_specifier"):
            continue
        name_node = child_by_field(child, "name")
        cname = text(name_node) if name_node else "?"
        body = child_by_field(child, "body")
        if body is None:
            continue
        methods = [
            n
            for n in body.named_children
            if n.type in ("function_definition", "declaration")
        ]
        n_methods = len(methods)
        if n_methods > max_class_methods:
            start_line = child.start_point[0] + 1
            out.append(
                ArchSuggestion(
                    file=rel,
                    line=start_line,
                    category="god-class",
                    severity="warning",
                    message=f"class `{cname}` has {n_methods} methods"
                    f" (threshold: {max_class_methods})",
                )
            )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze_project(
    root: Path,
    *,
    max_function_lines: int = 30,
    max_class_methods: int = 12,
    max_local_imports: int = 8,
    max_nesting_depth: int = 4,
    max_file_lines: int = 500,
) -> ArchResult:
    from frob.ast import cpp as _cpp
    from frob.ast import python as _py
    from frob.ast.cpp import ALL_EXTS as _CPP_EXTS

    suggestions: list[ArchSuggestion] = []
    all_py_sigs: list[tuple[str, str, tuple[str, ...], str]] = []

    files = _collect_files(root)

    for path in files:
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            continue

        ext = path.suffix.lower()

        try:
            raw = path.read_bytes()
        except OSError as exc:
            _log.debug("arch: cannot read %s: %s", rel, exc)
            continue

        lines = raw.splitlines()

        # large-file (all files)
        _check_large_file(path, rel, lines, max_file_lines, suggestions)

        if ext == ".py":
            try:
                _, tree = _py.parse_bytes(raw)
            except Exception as exc:
                _log.debug("arch: parse error in %s: %s", rel, exc)
                continue

            _py_check_long_functions(tree, rel, max_function_lines, suggestions)
            _py_check_god_classes(tree, rel, max_class_methods, suggestions)
            _py_check_high_coupling(tree, rel, root, max_local_imports, suggestions)
            _py_check_deep_nesting(tree, rel, max_nesting_depth, suggestions)

            sigs = _extract_py_signatures(tree, rel)
            all_py_sigs.extend(sigs)

        elif ext in _CPP_EXTS:
            try:
                _, tree = _cpp.parse_bytes(raw)
            except Exception as exc:
                _log.debug("arch: parse error in %s: %s", rel, exc)
                continue

            _cpp_check_long_functions(tree, rel, max_function_lines, suggestions)
            _cpp_check_god_classes(tree, rel, max_class_methods, suggestions)

    # cross-file check
    _check_abstraction_opportunities(all_py_sigs, suggestions)

    return ArchResult(root=str(root), suggestions=suggestions)

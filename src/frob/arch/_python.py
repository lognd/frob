"""Python architectural checks: long-function, god-class, high-coupling,
deep-nesting, and the cross-file abstraction-opportunity signature grouping
(docs/modules/arch.md's Python rules).

Every walker is driven off the one shared `_iter_py_functions` generator so
the recursion (into class bodies and nested functions) lives in exactly one
place instead of a bespoke nested closure per check.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from tree_sitter import Node, Tree

from frob.arch._models import ArchSuggestion
from frob.arch._nodes import _child, _node_text
from frob.logging import get_logger

_log = get_logger(__name__)

_NESTING_TYPES = frozenset(
    {
        "if_statement",
        "for_statement",
        "while_statement",
        "try_statement",
        "with_statement",
    }
)


def _iter_py_functions(
    node: Node, class_prefix: str = ""
) -> Iterator[tuple[Node, str, str]]:
    """Yield `(function_node, class_prefix, func_name)` for every function
    definition under `node`, recursing into class bodies (prefixing with the
    class name) and nested function bodies (prefix unchanged)."""
    for c in node.children:
        if c.type == "class_definition":
            name_node = _child(c, "name")
            cname = _node_text(name_node) if name_node else "?"
            body = _child(c, "body")
            if body:
                yield from _iter_py_functions(body, cname + ".")
        elif c.type == "function_definition":
            name_node = _child(c, "name")
            fname = _node_text(name_node) if name_node else "?"
            yield c, class_prefix, fname
            body = _child(c, "body")
            if body:
                yield from _iter_py_functions(body, class_prefix)


def _py_function_line_count(func_node: Node) -> int:
    """Line span of `func_node`'s body block (0 when it has no body)."""
    body = _child(func_node, "body")
    if body is None:
        return 0
    return body.end_point[0] - body.start_point[0] + 1


def _check_long_functions(
    tree: object,
    rel: str,
    max_function_lines: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag every python function whose body exceeds `max_function_lines`."""
    t: Tree = cast("Tree", tree)
    for func, prefix, fname in _iter_py_functions(t.root_node):
        n_lines = _py_function_line_count(func)
        if n_lines <= max_function_lines:
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=func.start_point[0] + 1,
                category="long-function",
                severity="warning",
                message=(
                    f"function `{prefix}{fname}` has"
                    f" {n_lines} lines (threshold: {max_function_lines})"
                ),
            )
        )


def _py_methods(body: Node) -> list[Node]:
    """The `function_definition` children directly inside a class body."""
    return [n for n in body.named_children if n.type == "function_definition"]


def _check_god_classes(
    tree: object,
    rel: str,
    max_class_methods: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag every top-level python class with more than `max_class_methods`."""
    t: Tree = cast("Tree", tree)
    for c in t.root_node.children:
        if c.type != "class_definition":
            continue
        body = _child(c, "body")
        if body is None:
            continue
        n_methods = len(_py_methods(body))
        if n_methods <= max_class_methods:
            continue
        name_node = _child(c, "name")
        cname = _node_text(name_node) if name_node else "?"
        out.append(
            ArchSuggestion(
                file=rel,
                line=c.start_point[0] + 1,
                category="god-class",
                severity="warning",
                message=f"class `{cname}` has {n_methods} methods"
                f" (threshold: {max_class_methods})",
            )
        )


def _check_high_coupling(
    path: Path,
    rel: str,
    root: Path,
    max_local_imports: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag python files importing more than `max_local_imports` local modules."""
    from frob.lang import extract_imports, resolve_local_import

    specs_result = extract_imports(path)
    if specs_result.is_err:
        _log.debug("high-coupling: failed to parse %s: %s", rel, specs_result.err)
        return
    resolved = {
        resolve_local_import(spec, "python", file_dir=path.parent, root=root)
        for spec in specs_result.danger_ok
    }
    resolved.discard(None)
    n = len(resolved)
    if n > max_local_imports:
        out.append(
            ArchSuggestion(
                file=rel,
                category="high-coupling",
                severity="suggestion",
                message=f"file imports {n} local modules (threshold: {max_local_imports})",  # noqa: E501
            )
        )


def _py_max_nesting(func_body_node: Node) -> int:
    """Deepest control-flow nesting depth inside a function body block."""

    def depth(node: Node, current: int) -> int:
        best = current
        for c in node.children:
            nxt = current + 1 if c.type in _NESTING_TYPES else current
            best = max(best, depth(c, nxt))
        return best

    return depth(func_body_node, 0)


def _check_deep_nesting(
    tree: object,
    rel: str,
    max_nesting_depth: int,
    out: list[ArchSuggestion],
) -> None:
    """Flag python functions whose control-flow nesting exceeds the threshold."""
    t: Tree = cast("Tree", tree)
    for func, prefix, fname in _iter_py_functions(t.root_node):
        body = _child(func, "body")
        if body is None:
            continue
        depth = _py_max_nesting(body)
        if depth <= max_nesting_depth:
            continue
        out.append(
            ArchSuggestion(
                file=rel,
                line=func.start_point[0] + 1,
                category="deep-nesting",
                severity="suggestion",
                message=(
                    f"function `{prefix}{fname}` has"
                    f" nesting depth {depth}"
                    f" (threshold: {max_nesting_depth})"
                ),
            )
        )


def _annotation_text(node: Node) -> str:
    """The stripped source text of a type-annotation node."""
    return _node_text(node).strip()


def _py_param_types(func_node: Node) -> list[str]:
    """Annotated parameter type texts of `func_node` (unannotated skipped)."""
    params_node = _child(func_node, "parameters")
    if params_node is None:
        return []
    types: list[str] = []
    for p in params_node.named_children:
        if p.type in ("typed_parameter", "typed_default_parameter"):
            ann = _child(p, "type")
            if ann:
                types.append(_annotation_text(ann))
    return types


def _extract_signatures(
    tree: object,
    rel: str,
) -> list[tuple[str, str, tuple[str, ...], str]]:
    """`(rel, func_name, param_types, return_type)` for every python function
    carrying at least one annotated parameter or an annotated return type."""
    t: Tree = cast("Tree", tree)
    results: list[tuple[str, str, tuple[str, ...], str]] = []
    for func, _prefix, fname in _iter_py_functions(t.root_node):
        param_types = _py_param_types(func)
        ret_node = _child(func, "return_type")
        ret = _annotation_text(ret_node) if ret_node else ""
        if param_types or ret:
            results.append((rel, fname, tuple(param_types), ret))
    return results


def _check_abstraction_opportunities(
    all_sigs: list[tuple[str, str, tuple[str, ...], str]],
    out: list[ArchSuggestion],
) -> None:
    """Flag signatures shared by 3+ functions (a possible shared abstraction)."""
    groups: dict[tuple[tuple[str, ...], str], list[tuple[str, str]]] = defaultdict(list)
    for rel, fname, ptypes, ret in all_sigs:
        if not ptypes:
            continue
        groups[(ptypes, ret)].append((rel, fname))

    for (ptypes, ret), members in groups.items():
        if len(members) < 3:
            continue
        params_str = ", ".join(ptypes)
        sig_str = f"({params_str}) -> {ret}" if ret else f"({params_str})"
        fn_names = ", ".join(fname for _, fname in members)
        out.append(
            ArchSuggestion(
                file=members[0][0],
                category="abstraction-opportunity",
                severity="suggestion",
                message=(
                    f"{len(members)} functions share signature `{sig_str}`: {fn_names}"
                ),
                detail="Consider a shared protocol or base class",
            )
        )

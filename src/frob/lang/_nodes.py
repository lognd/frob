"""Tree-sitter node utilities shared by `frob.arch` and `frob.dup._legacy`
(T-0989, split out of `frob.lang.__init__` per T-0980's ARCH102 waiver:
these four exports have no shared state and no call edges into the rest
of `frob.lang`, unlike the extension-table and parse-cache groups that
remain in `__init__.py`).

Re-exported from `frob.lang` so every existing
`from frob.lang import cpp_function_nodes` (etc.) caller is unaffected --
this module is not meant to be imported directly by callers outside
`frob.lang`.
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Node, Tree

from frob.lang._common import child_by_field as _child_by_field
from frob.lang._common import child_text as _child_text
from frob.lang._common import iter_cpp_functions as _iter_cpp_functions


# frob:doc docs/modules/graph.md#public-api
def cpp_function_nodes(tree: Tree) -> tuple[tuple[Node, str], ...]:
    """(node, qualified_name) for every C/C++ function in `tree` (one level
    of class/struct nesting). Thin public wrapper around
    `frob.lang._common.iter_cpp_functions` -- see its docstring for the
    exact walk semantics `frob.arch` and `frob.dup._legacy` share."""
    return _iter_cpp_functions(tree.root_node)


# frob:doc docs/modules/graph.md#public-api
def child_by_field(node: Node, field: str) -> Node | None:
    """`node.child_by_field_name(field)`, exposed so `frob.arch` and
    `frob.dup._legacy`'s raw-node walks share one field-lookup call
    instead of each keeping a local copy (see `frob.lang._common`)."""
    return _child_by_field(node, field)


# frob:doc docs/modules/graph.md#public-api
def node_text(node: Node | None) -> str:
    """Decode `node`'s own text, or '' if absent. Public alias of
    `frob.lang._common.child_text` for callers doing raw node traversal
    outside the extraction pipeline (`frob.arch`, `frob.dup._legacy`)."""
    return _child_text(node)


# frob:doc docs/modules/graph.md#public-api
# frob:waive TEST005 reason="resolve_local_import 57.1% branch cover, debt T-0160"
def resolve_local_import(
    specifier: str, language: str, *, file_dir: Path, root: Path
) -> str | None:
    """Resolve a raw `extract_imports` specifier to a `root`-relative path.

    Returns `None` when the specifier does not point at a file that exists
    under `root` (a third-party import, a system `<...>` include already
    filtered out upstream, etc.) -- `frob.cycle` skips those rather than
    adding a graph edge to nowhere.
    """
    if language == "python":
        base = specifier.replace(".", "/")
        for suffix in (".py", "/__init__.py"):
            candidate = Path(base + suffix)
            if (root / candidate).exists():
                return candidate.as_posix()
        return None
    if language in ("c", "cpp"):
        candidate = (file_dir / specifier).resolve()
        try:
            rel = candidate.relative_to(root.resolve())
        except ValueError:
            return None
        return rel.as_posix() if candidate.exists() else None
    return None


__all__ = [
    "child_by_field",
    "cpp_function_nodes",
    "node_text",
    "resolve_local_import",
]

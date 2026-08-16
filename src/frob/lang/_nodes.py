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

import functools
from pathlib import Path

from tree_sitter import Node, Tree

from frob.lang._common import _child_text as _child_text
from frob.lang._common import _iter_cpp_functions as _iter_cpp_functions
from frob.lang._common import child_by_field as _child_by_field


@functools.lru_cache(maxsize=32)
def _declared_python_source_roots(root: Path) -> tuple[Path, ...]:
    """Python source roots `root`'s own `pyproject.toml` declares (T-2195).

    A src-layout project (`[tool.setuptools] packages = { find = { where =
    ["src"] } }`, or the equivalent `package-dir`/hatch-wheel-packages
    forms) imports its own top-level packages as `frob.x`, not `src.frob.
    x` -- the specifier text never mentions `src/` at all, so resolving it
    against bare `root` alone (the pre-T-2195 behavior) silently fails for
    every absolute intra-repo import in a src-layout repo. This reads the
    project's OWN declared packaging config to find every additional root
    an absolute specifier might live under, instead of hardcoding the
    `src/` convention as a lexical special case -- a different declared
    layout (`lib/`, a namespace package) is picked up the same way, with
    no code change here. `root` itself is always included last as a
    fallback for a project with no src-layout at all (the historical,
    still-supported case: `tests/unit/test_lang_primitives.py::
    test_resolve_local_import_maps_to_repo_relative`). Cached per-root
    (`lru_cache`) since `resolve_local_import` calls this once per
    specifier and a repo-wide scan calls it thousands of times per run;
    `root` is a stable identity for the lifetime of one such scan.
    """
    roots: list[Path] = []
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        import tomllib

        try:
            with pyproject.open("rb") as fh:
                data = tomllib.load(fh)
        except (OSError, tomllib.TOMLDecodeError):
            data = {}
        tool_cfg = data.get("tool", {}) if isinstance(data, dict) else {}
        setuptools_cfg = tool_cfg.get("setuptools", {})
        if isinstance(setuptools_cfg, dict):
            packages_cfg = setuptools_cfg.get("packages")
            if isinstance(packages_cfg, dict):
                find_cfg = packages_cfg.get("find")
                if isinstance(find_cfg, dict):
                    for where in find_cfg.get("where") or []:
                        if isinstance(where, str):
                            roots.append(root / where)
            package_dir = setuptools_cfg.get("package-dir")
            if isinstance(package_dir, dict):
                for value in package_dir.values():
                    if isinstance(value, str) and value:
                        roots.append(root / value)
        hatch_wheel_cfg = (
            tool_cfg.get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {})
        )
        if isinstance(hatch_wheel_cfg, dict):
            for pkg in hatch_wheel_cfg.get("packages") or []:
                if isinstance(pkg, str) and pkg:
                    roots.append((root / pkg).parent)
    roots.append(root)
    seen: set[str] = set()
    deduped: list[Path] = []
    for candidate_root in roots:
        key = candidate_root.as_posix()
        if key not in seen:
            seen.add(key)
            deduped.append(candidate_root)
    return tuple(deduped)


def _resolve_under(base_no_suffix: Path, root: Path) -> str | None:
    """First of `base_no_suffix.py` / `base_no_suffix/__init__.py` that
    exists, as a `root`-relative posix path, or `None` -- the shared
    existence-check `resolve_local_import`'s python branch (both the
    absolute and relative forms) reduces to once a candidate module
    directory is computed."""
    for suffix in (".py", "/__init__.py"):
        candidate = Path(base_no_suffix.as_posix() + suffix)
        try:
            found = candidate.exists()
        except OSError:
            continue
        if not found:
            continue
        try:
            return candidate.relative_to(root).as_posix()
        except ValueError:
            return None
    return None


def _resolve_absolute_python_import(specifier: str, *, root: Path) -> str | None:
    """Resolve an absolute python specifier (`frob.tickets._land`) against
    every declared source root (T-2195) -- `root` itself plus any
    `pyproject.toml`-declared package root (`src/`, etc)."""
    base_rel = specifier.replace(".", "/")
    for source_root in _declared_python_source_roots(root):
        resolved = _resolve_under(source_root / base_rel, root)
        if resolved is not None:
            return resolved
    return None


def _resolve_relative_python_import(
    specifier: str, *, file_dir: Path, root: Path
) -> str | None:
    """Resolve a relative python specifier (`._land`, `..lang._nodes`)
    against the importing file's OWN package position (T-2195) -- no
    `pyproject.toml`/source-root lookup needed, since a relative import is
    always anchored at the importer's own directory: `file_dir` already IS
    the package the importing module lives in (one leading dot means
    "this same package"), so each additional dot walks one directory up
    from there, mirroring python's own relative-import semantics."""
    level = len(specifier) - len(specifier.lstrip("."))
    rest = specifier[level:]
    base = file_dir
    for _ in range(level - 1):
        base = base.parent
    if not rest:
        candidate = base / "__init__.py"
        try:
            found = candidate.exists()
        except OSError:
            return None
        if not found:
            return None
        try:
            return candidate.relative_to(root).as_posix()
        except ValueError:
            return None
    return _resolve_under(base.joinpath(*rest.split(".")), root)


# frob:doc docs/modules/graph.md#public-api
def cpp_function_nodes(tree: Tree) -> tuple[tuple[Node, str], ...]:
    """(node, qualified_name) for every C/C++ function in `tree` (one level
    of class/struct nesting). Thin public wrapper around
    `frob.lang._common._iter_cpp_functions` -- see its docstring for the
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
    `frob.lang._common._child_text` for callers doing raw node traversal
    outside the extraction pipeline (`frob.arch`, `frob.dup._legacy`)."""
    return _child_text(node)


# frob:doc docs/modules/graph.md#public-api
# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to str.replace/Path. as_posix, \
# plain str/pathlib calls the resolver cannot statically bound; every real raise path \
# (path existence/resolve checks) is caught in each language branch"
# frob:waive AFFECT001 reason="T-1062: EXHAUST001 hardening -- widened OSError \
# handling around Path.exists()/Path.resolve() in both language branches; the \
# documented 'None when unresolvable' return contract and behavior are unchanged, \
# nothing for docs/modules/graph.md#public-api to update"
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
        if specifier.startswith("."):
            return _resolve_relative_python_import(
                specifier, file_dir=file_dir, root=root
            )
        return _resolve_absolute_python_import(specifier, root=root)
    if language in ("c", "cpp"):
        try:
            candidate = (file_dir / specifier).resolve()
            rel = candidate.relative_to(root.resolve())
            exists = candidate.exists()
        except (OSError, ValueError):
            return None
        return rel.as_posix() if exists else None
    return None


__all__ = [
    "child_by_field",
    "cpp_function_nodes",
    "node_text",
    "resolve_local_import",
]

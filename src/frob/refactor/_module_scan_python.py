"""Python `move-module` adapter (T-2990): the reference-kind inventory
for a whole-MODULE move, as opposed to `_scan.py`'s single-symbol
`from <module> import <qualname>` scope.

A module reference is spelled four ways in Python source, all handled
here, symbolically (AST-node comparison, never substring matching -- a
prefix-colliding sibling module is never touched because every match
below compares a FULL dotted-name list for exact equality, not a text
prefix):

1. `import old.module[ as x]` -- rewrites the import statement; when no
   `asname` is given, every `old.module.symbol` attribute-chain usage
   elsewhere in the file is also repointed (the binding Python creates
   for a bare `import a.b` is the top-level name `a`, accessed via the
   full dotted chain).
2. `from old.pkg import old_leaf[ as x]` -- the "from PARENT import
   MODULE" form. Repoints the imported name; when no `asname` is given,
   bare-name usages of `old_leaf` elsewhere in the file are rewritten to
   the new leaf name (reuses `_scan._rename_usages`, the identical
   mechanism the symbol engine already uses for this exact shape).
3. `from old.module import name[, ...]` -- rewrites just the module
   half of the statement; the imported names are untouched (the module
   moved, not any symbol in it).
4. A relative import (`node.level > 0`) resolving to the old module
   under either shape 2 or 3 above -- resolved to an absolute dotted
   path first (`_resolve_relative`), then handled identically; rewritten
   back to a relative form when the importing file's own package is
   unchanged relative to the destination, else converted to an absolute
   import (always correct regardless of how the move changes package
   depth).

Plus one dynamic-reference detector: a literal string argument to
`importlib.import_module(...)`/`__import__(...)` equal to the old
dotted module path is rewritten in place; anything else passed to
either call is out of static-AST scope and is neither guessed at nor
silently dropped.

Deliberately does NOT touch comments or docstrings -- a prose mention of
the module (a docstring discussing it, a log message, a test fixture's
literal text) is not a reference, and this file's whole contract is
node-level AST matching, which never sees comments and only inspects
string constants that are themselves the argument to a dynamic-import
call. (Repo-wide prose/config/docs citations of the dotted path or file
path are `_module_prose.py`'s job, not this module's.)
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TYPE_CHECKING

from frob.logging import get_logger
from frob.refactor._models import AliasRecord, RewriteOp
from frob.refactor._scan import _rename_usages, find_python_files

if TYPE_CHECKING:
    from frob.refactor._module_resolve import ResolvedModule
    from frob.refactor._operands import ModuleRef

_log = get_logger(__name__)

__all__ = ["scan_python_module_references"]


def _package_of(module: str) -> str:
    """The dotted parent package of `module`, or `""` for a top-level
    module -- `"a.b.c"` -> `"a.b"`, `"top"` -> `""`."""
    return module.rsplit(".", 1)[0] if "." in module else ""


def _ancestor(package: str, levels_up: int) -> str:
    """`package` with `levels_up` trailing dotted components dropped --
    the absolute-package arithmetic a relative import's `level` encodes
    (`level - 1` steps up from the CURRENT module's own package, per
    Python's import semantics)."""
    if levels_up <= 0:
        return package
    parts = package.split(".") if package else []
    remaining = len(parts) - levels_up
    return ".".join(parts[:remaining]) if remaining > 0 else ""


def _importing_package(repo_root: Path, file_path: Path) -> str:
    """The dotted package a `.py` file under `src/` (or `repo_root`)
    itself belongs to -- `src/frob/gates/decisions.py` ->
    `"frob.gates"`, `src/frob/legacy_io.py` -> `"frob"`. Used to resolve
    that FILE's own relative imports to an absolute target, and to
    decide whether a rewritten import can stay relative."""
    src_root = repo_root / "src"
    base = src_root if src_root.is_dir() else repo_root
    try:
        rel = file_path.relative_to(base)
    except ValueError:
        return ""
    # Dropping the trailing path component gives the right package
    # either way: for a plain module `pkg/sub/mod.py` that component is
    # the module's own name (package `pkg.sub`); for `pkg/__init__.py`
    # it is the literal `__init__` component, and what remains IS the
    # package `pkg` itself.
    parts = rel.with_suffix("").parts
    return ".".join(parts[:-1])


def _resolve_relative(importing_package: str, node: ast.ImportFrom) -> str | None:
    """The absolute dotted module `node` (a relative `ImportFrom`, i.e.
    `node.level > 0`) targets, given the file it lives in belongs to
    `importing_package` -- the "from MODULE import name" shape's own
    resolution (distinct from `_relative_parent_value`, which resolves
    only the "from PARENT import MODULE" shape's parent half)."""
    base = _ancestor(importing_package, node.level - 1)
    return f"{base}.{node.module}" if node.module else base


def _dotted_attribute_chain(node: ast.expr) -> list[str] | None:
    """Every segment of an `Attribute`/`Name` chain as a list (`['frob',
    'legacy_io', 'fast_loader']`), or `None` if any link is not a
    plain `Name`/`Attribute` -- mirrors `_scan._dotted_attribute_chain`
    but returns the SEGMENT LIST (not a joined string) so a caller can
    do exact-length prefix comparison instead of string-prefix matching
    (the prefix-collision guard: `['frob','legacy_io']` must never match
    `['frob','legacy_io_extra']`, which a string `.startswith` check
    would risk if not paired with a boundary check -- a list compare has
    no such hazard)."""
    parts: list[str] = []
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return None
    parts.append(cur.id)
    return list(reversed(parts))


def _splice_span(
    file_path: Path,
    source_lines: list[str],
    node: ast.expr,
    replacement: str,
    reason: str,
) -> RewriteOp | None:
    """One `RewriteOp` replacing `node`'s own `[lineno, col_offset)` ..
    `[end_lineno, end_col_offset)` span with `replacement` -- `None` if
    the span crosses multiple physical lines (a parenthesized multi-line
    attribute chain), which this function refuses to splice rather than
    risk a wrong column offset on a reflowed line; the caller records
    that case as `unresolved` instead."""
    if node.end_lineno is None or node.lineno != node.end_lineno:
        return None
    line = source_lines[node.lineno - 1]
    new_line = line[: node.col_offset] + replacement + line[node.end_col_offset :]
    return RewriteOp(
        file_path=str(file_path),
        start_line=node.lineno,
        end_line=node.lineno,
        old_text=line,
        new_text=new_line,
        reason=reason,
    )


def _rewrite_bare_import(
    file_path: Path,
    source_lines: list[str],
    tree: ast.Module,
    node: ast.Import,
    alias: ast.alias,
    old_module: str,
    new_module: str,
) -> list[RewriteOp]:
    """`import old.module[ as x]` -- rewrite the import statement itself,
    plus (only when unaliased) every `old.module.symbol`-shaped
    attribute-chain usage elsewhere in the file."""
    ops: list[RewriteOp] = []
    old_stmt = f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else "")
    new_name = new_module + (f" as {alias.asname}" if alias.asname else "")
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    if node.lineno == end:
        line = source_lines[node.lineno - 1]
        idx = line.find(old_stmt)
        if idx != -1:
            new_line = line[:idx] + f"import {new_name}" + line[idx + len(old_stmt) :]
            ops.append(
                RewriteOp(
                    file_path=str(file_path),
                    start_line=node.lineno,
                    end_line=node.lineno,
                    old_text=line,
                    new_text=new_line,
                    reason=f"rewrite `import {old_module}` -> `import {new_module}`",
                )
            )
    if alias.asname:
        return ops  # bound name unchanged; no usage sites to rewrite

    old_parts = old_module.split(".")
    for sub in ast.walk(tree):
        if not isinstance(sub, ast.Attribute) or sub.lineno == node.lineno:
            continue
        # `ast.walk` visits every nested `Attribute` node individually
        # (for `pkg.old_mod.symbol`, both the outer `pkg.old_mod.symbol`
        # node AND the inner `pkg.old_mod` node are yielded) -- matching
        # on EXACT chain equality here, rather than a prefix match plus
        # `_prefix_node` extraction, means each usage site is matched
        # exactly once, at the innermost node whose own chain equals
        # `old_parts`, instead of once per containing outer chain too
        # (which would splice the identical span twice and trip
        # `apply_ops`'s overlap guard).
        chain = _dotted_attribute_chain(sub)
        if chain != old_parts:
            continue
        op = _splice_span(
            file_path,
            source_lines,
            sub,
            new_module,
            reason=f"attribute-chain rename {old_module} -> {new_module}",
        )
        if op is not None:
            ops.append(op)
    return ops


# frob:waive DUP001 reason="_scan._rebuild_from_import builds a from-import statement \
# for a SYMBOL rename (always drops the alias, appends the destination qualname \
# unaliased); this builds one for a MODULE-as-name rewrite (preserves the call site's \
# own `as x` aliasing, since a module rename must not silently change what name a \
# caller binds it under) -- structurally similar comprehension-then-join shape, \
# different domain data and different aliasing semantics, no shared behavior to extract"
def _rewrite_from_module_import_leaf(
    file_path: Path,
    source: str,
    tree: ast.Module,
    node: ast.ImportFrom,
    alias: ast.alias,
    new_parent: str,
    new_leaf: str,
) -> list[RewriteOp]:
    """`from old_parent import old_leaf[ as x]` -- the "from PARENT
    import MODULE" shape, absolute or already-resolved-from-relative.
    Rewrites the import statement's names list, and (only when unaliased)
    every bare-name usage of `old_leaf` via the SAME `_rename_usages`
    helper `_scan.py`'s symbol engine already uses for this identical
    problem (T-2990's reuse directive: do not fork this)."""
    others = [a for a in node.names if a is not alias]
    parts = [f"{a.name} as {a.asname}" if a.asname else a.name for a in others]
    new_alias_text = f"{new_leaf} as {alias.asname}" if alias.asname else new_leaf
    parts.append(new_alias_text)
    new_stmt = f"from {new_parent} import {', '.join(parts)}"
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    ops = [
        RewriteOp(
            file_path=str(file_path),
            start_line=node.lineno,
            end_line=end,
            old_text=f"<import at line {node.lineno}>",
            new_text=new_stmt,
            reason=(
                f"rewrite `from {node.module or ''} import {alias.name}` "
                f"-> `from {new_parent} import {new_leaf}`"
            ),
        )
    ]
    if alias.asname is None:
        ops.extend(
            _rename_usages(
                file_path, source, tree, alias.name, new_leaf, exclude_line=node.lineno
            )
        )
    return ops


def _rewrite_from_module_import_names(
    file_path: Path, node: ast.ImportFrom, new_module: str
) -> RewriteOp:
    """`from old.module import name[, ...]` -- only the module half of
    the statement changes; the imported names are untouched (they still
    name the same symbols, just in the module's new home)."""
    names = [f"{a.name} as {a.asname}" if a.asname else a.name for a in node.names]
    new_stmt = f"from {new_module} import {', '.join(names)}"
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    return RewriteOp(
        file_path=str(file_path),
        start_line=node.lineno,
        end_line=end,
        old_text=f"<import at line {node.lineno}>",
        new_text=new_stmt,
        reason=f"rewrite `from {node.module}` -> `from {new_module}`",
    )


def _relative_parent_value(importing_package: str, node: ast.ImportFrom) -> str:
    """The absolute dotted PACKAGE `node`'s relative `from X import ...`
    names, when `node` is itself relative (`node.level > 0`) -- e.g.
    `from . import legacy_io` (level=1, module=None) resolves to
    `importing_package` itself; `from .sub import x` (level=1,
    module='sub') resolves to `importing_package.sub`. Distinct from
    `_resolve_relative`, which resolves the FULL target including
    `node.names` for the `from MODULE import name` shape -- this
    resolves only the PARENT half, for the `from PARENT import MODULE`
    shape `_handle_import_from` handles."""
    base = _ancestor(importing_package, node.level - 1)
    if not node.module:
        return base
    return f"{base}.{node.module}" if base else node.module


def _handle_import_from(
    file_path: Path,
    source: str,
    tree: ast.Module,
    node: ast.ImportFrom,
    old_module: str,
    new_module: str,
    new_parent: str,
    new_leaf: str,
    importing_package: str,
) -> list[RewriteOp]:
    """`from <parent> import <old_leaf>[ as x]` -- the "from PARENT
    import MODULE" shape, absolute or relative. Resolves the effective
    parent package (absolute `node.module`, or the relative-import
    arithmetic in `_relative_parent_value`) and compares it against
    `old_module`'s own parent; a match plus `alias.name == old_leaf`
    is the only condition that fires this shape, distinct from
    `_scan_module_import_from`'s "from MODULE import name" shape below
    (mutually exclusive: one compares the PARENT, the other compares
    the full MODULE path -- a parent can never equal its own child's
    full dotted path)."""
    old_parent = _package_of(old_module)
    old_leaf = old_module.rsplit(".", 1)[-1] if "." in old_module else old_module

    if node.level > 0:
        parent_value = _relative_parent_value(importing_package, node)
    else:
        parent_value = node.module or ""

    if parent_value != old_parent:
        return []

    for alias in node.names:
        if alias.name != old_leaf:
            continue
        if node.level > 0 and _importing_relative_still_valid(
            importing_package, new_parent
        ):
            target_parent = "." * node.level
        else:
            target_parent = new_parent
        return _rewrite_from_module_import_leaf(
            file_path, source, tree, node, alias, target_parent, new_leaf
        )
    return []


def _importing_relative_still_valid(importing_package: str, new_parent: str) -> bool:
    """`True` iff `new_parent` is `importing_package` itself -- the only
    case this engine re-expresses a rewritten import as relative again
    (`from . import new_leaf`); any other relationship (the move changed
    which package the module lives in relative to the importing file)
    falls back to an absolute import, which is always correct regardless
    of how the move changed package depth."""
    return new_parent == importing_package


def _scan_module_import_from(
    file_path: Path,
    source: str,
    tree: ast.Module,
    node: ast.ImportFrom,
    old_module: str,
    new_module: str,
    new_parent: str,
    importing_package: str,
) -> list[RewriteOp]:
    """`from old.module import name[, ...]` (absolute or relative,
    resolved to `old_module` exactly) -- rewrite the module half only.
    Stays relative iff the importing file's OWN package equals
    `new_parent` (the PACKAGE the destination module lives in, not the
    destination module's own full dotted path -- comparing against
    `new_module` here was T-2990's own bug during development: it made
    `from . import new_leaf` never re-form because `importing_package`
    ("pkg") can never equal `new_module` ("pkg.new_mod"))."""
    if node.level > 0:
        absolute = _resolve_relative(importing_package, node)
    else:
        absolute = node.module
    if absolute != old_module:
        return []
    if node.level > 0 and _importing_relative_still_valid(
        importing_package, new_parent
    ):
        # Same package before and after the move: relative import stays
        # relative, only the module NAME part (if any) changes -- but a
        # `from .old_module import X` shape has `node.module == leaf`,
        # not the full dotted path, so rebuild from the new leaf.
        new_leaf = new_module.rsplit(".", 1)[-1] if "." in new_module else new_module
        end = node.end_lineno if node.end_lineno is not None else node.lineno
        names = [f"{a.name} as {a.asname}" if a.asname else a.name for a in node.names]
        return [
            RewriteOp(
                file_path=str(file_path),
                start_line=node.lineno,
                end_line=end,
                old_text=f"<import at line {node.lineno}>",
                new_text=f"from {'.' * node.level}{new_leaf} import {', '.join(names)}",
                reason=(
                    f"rewrite relative `from {'.' * node.level}{node.module} "
                    f"import ...` -> `from {'.' * node.level}{new_leaf} import ...`"
                ),
            )
        ]
    return [_rewrite_from_module_import_names(file_path, node, new_module)]


def _scan_dynamic_import(
    file_path: Path,
    source_lines: list[str],
    tree: ast.Module,
    old_module: str,
    new_module: str,
) -> tuple[list[RewriteOp], list[str]]:
    """`importlib.import_module("old.module")` / `__import__("old.module")`
    -- a literal string argument equal to `old_module` is rewritten in
    place; any other call to either function is out of this static-AST
    scanner's scope and is neither guessed at nor flagged (a computed
    argument could name anything)."""
    ops: list[RewriteOp] = []
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        is_import_module = (
            isinstance(func, ast.Attribute)
            and func.attr == "import_module"
            and isinstance(func.value, ast.Name)
            and func.value.id == "importlib"
        ) or (isinstance(func, ast.Name) and func.id == "__import__")
        if not is_import_module or not call.args:
            continue
        arg = call.args[0]
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
            continue
        if arg.value != old_module:
            continue
        op = _splice_span(
            file_path,
            source_lines,
            arg,
            repr(new_module),
            reason=f"dynamic import string {old_module!r} -> {new_module!r}",
        )
        if op is not None:
            ops.append(op)
    return ops, []


def _scan_tree_nodes(
    file_path: Path,
    source: str,
    source_lines: list[str],
    tree: ast.Module,
    old_module: str,
    new_module: str,
    new_parent: str,
    new_leaf: str,
    importing_package: str,
) -> list[RewriteOp]:
    """Every `ast.Import`/`ast.ImportFrom` node's rewrite ops for one
    already-parsed file -- the AST-walk body split out of `_scan_one_
    file` (ARCH001, T-2990) so that function stays a thin parse-then-
    dispatch-then-catch shell."""
    ops: list[RewriteOp] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name != old_module:
                    continue
                ops.extend(
                    _rewrite_bare_import(
                        file_path,
                        source_lines,
                        tree,
                        node,
                        alias,
                        old_module,
                        new_module,
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            ops.extend(
                _handle_import_from(
                    file_path,
                    source,
                    tree,
                    node,
                    old_module,
                    new_module,
                    new_parent,
                    new_leaf,
                    importing_package,
                )
            )
            ops.extend(
                _scan_module_import_from(
                    file_path,
                    source,
                    tree,
                    node,
                    old_module,
                    new_module,
                    new_parent,
                    importing_package,
                )
            )
    return ops


def _scan_one_file(
    repo_root: Path,
    file_path: Path,
    old_module: str,
    new_module: str,
    new_parent: str,
    new_leaf: str,
) -> tuple[list[RewriteOp], list[str]]:
    """One file's whole import-form inventory -- every `ast.Import`/
    `ast.ImportFrom` node (via `_scan_tree_nodes`) plus the dynamic-
    import detector. Split out of `scan_python_module_references`
    (ARCH001, T-2990) so the repo-wide loop stays a thin per-file
    dispatch; a per-file AST-shape surprise becomes a disclosed
    `unresolved` entry here, never an abort of the whole repo scan
    (matching `_scan.scan_references`'s own posture)."""
    ops: list[RewriteOp] = []
    unresolved: list[str] = []
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except (OSError, SyntaxError):
        return ops, unresolved

    source_lines = source.splitlines()
    importing_package = _importing_package(repo_root, file_path)

    try:
        ops.extend(
            _scan_tree_nodes(
                file_path,
                source,
                source_lines,
                tree,
                old_module,
                new_module,
                new_parent,
                new_leaf,
                importing_package,
            )
        )
        dyn_ops, dyn_unresolved = _scan_dynamic_import(
            file_path, source_lines, tree, old_module, new_module
        )
        ops.extend(dyn_ops)
        unresolved.extend(dyn_unresolved)
    except (KeyError, TypeError, ValueError) as exc:
        unresolved.append(f"{file_path}: module scan failed unexpectedly ({exc})")
    return ops, unresolved


# frob:doc docs/commands/refactor.md#scan_python_module_references
# frob:tests tests/test_refactor.py::TestModuleScanPython.test_rewrites_plain_import
# frob:tests tests/test_refactor.py::TestModuleScanPython.test_rewrites_aliased_import
# frob:tests tests/test_refactor.py::TestModuleScanPython.test_rewrites_from_package_import_module  # noqa: E501
# frob:tests tests/test_refactor.py::TestModuleScanPython.test_rewrites_from_module_import_name  # noqa: E501
# frob:tests tests/test_refactor.py::TestModuleScanPython.test_rewrites_relative_import
# frob:tests tests/test_refactor.py::TestModuleScanPython.test_rewrites_init_reexport
# frob:tests tests/test_refactor.py::TestModuleScanPython.test_rewrites_dynamic_import_module  # noqa: E501
# frob:tests tests/test_refactor.py::TestModuleScanPython.test_leaves_prefix_colliding_sibling_untouched  # noqa: E501
def scan_python_module_references(
    repo_root: Path, resolved: "ResolvedModule", destination: "ModuleRef"
) -> tuple[list[RewriteOp], list[AliasRecord], list[str]]:
    """The Python `move-module` adapter's whole reference-kind inventory:
    walk every `.py` file (the moved file's own source included, for its
    own relative imports) and rewrite every AST-provable reference to
    `resolved.ref.module`, exactly as spelled -- plain import, aliased
    import, `from PARENT import MODULE`, `from MODULE import name`,
    relative forms of either, and a literal dynamic `importlib.
    import_module`/`__import__` string. No aliases are auto-generated
    here (module names, unlike symbol names, cannot collide with an
    existing binding the way `_scan.scan_references`'s destination-leaf
    collision can) -- the second return value is always empty; kept for
    call-shape parity with the symbol engine's scanner."""
    old_module = resolved.ref.module
    new_module = destination.module
    new_parent = _package_of(new_module)
    new_leaf = new_module.rsplit(".", 1)[-1] if "." in new_module else new_module

    ops: list[RewriteOp] = []
    unresolved: list[str] = []

    for file_path in find_python_files(repo_root):
        file_ops, file_unresolved = _scan_one_file(
            repo_root, file_path, old_module, new_module, new_parent, new_leaf
        )
        ops.extend(file_ops)
        unresolved.extend(file_unresolved)

    _log.info(
        "refactor.module_scan_python: %s -> %s: %d reference op(s), %d unresolved",
        old_module,
        new_module,
        len(ops),
        len(unresolved),
    )
    return ops, [], unresolved

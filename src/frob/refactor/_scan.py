"""Plan phase: enumerate every Python import/call-site reference to a
moving symbol, repo-wide, before any file write
(docs/design/refactor-verb.md's reference-kind inventory, "Python
imports/call sites" row).

This is the one reference-kind row T-1197 owns directly; the sibling
DSL/registry/prose carriers (T-1199/T-1200/T-1267) extend the same
`RefactorPlan.reference_ops`/`aliases` shape with their own scan passes
rather than reimplementing this walk (docs/design/refactor-verb.md's
"Children filed" section).
"""

from __future__ import annotations

import ast
from pathlib import Path

from frob.excludes import walk_pruned
from frob.logging import get_logger
from frob.refactor._models import AliasRecord, ResolvedSymbol, RewriteOp, SymbolRef
from frob.refactor._scan_carry import (  # noqa: F401 -- T-1201 split re-export
    needed_import_ops_for_symbols,
    stale_dest_import_ops,
)
from frob.refactor._scan_repoint import (
    _handle_import,
    _shares_line_with_sibling_statement,
    bare_name_repoint_ops,  # noqa: F401 -- T-1201 split re-export
)

_log = get_logger(__name__)

__all__ = [
    "bare_name_repoint_ops",
    "find_python_files",
    "needed_import_ops_for_symbols",
    "scan_references",
    "stale_dest_import_ops",
]


# frob:doc docs/commands/refactor.md#find_python_files
# frob:tests tests/test_refactor.py::TestFindPythonFiles.test_finds_py_files_and_skips_venv  # noqa: E501
# frob:ticket T-1504
def find_python_files(repo_root: Path) -> list[Path]:
    """Every `.py` file under `repo_root`, skipping VCS/build/venv
    directories -- the repo-wide walk both the scan and the Verify
    phase's import-resolution check reuse. Routed through
    `frob.excludes.walk_pruned` (T-1478, WALK001) so pruning happens
    before descent instead of after a full unpruned `rglob` -- deliberately
    NOT `frob.excludes.iter_files`, whose `git ls-files` fast path would
    silently skip untracked `.py` files a refactor is actively creating or
    has not yet `git add`ed."""
    return sorted(p for p in walk_pruned(repo_root) if p.suffix == ".py")


def _existing_bound_names(tree: ast.Module) -> set[str]:
    """Every name already bound at module scope by an import statement --
    used to detect an alias collision at a call site (Plan phase, alias-
    conflict policy's default `error`-becomes-auto-alias path)."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _alias_collision_rewrite(
    file_path: Path,
    source: str,
    tree: ast.Module,
    node: ast.ImportFrom,
    destination: SymbolRef,
    new_name: str,
    bound_as: str,
    reason: str,
) -> tuple[list[RewriteOp], AliasRecord]:
    """Auto-alias rewrite for a single colliding `from`-import name (the
    `alias_conflict == "error"` collision branch of `_handle_from_import`,
    split out to keep that function under the ARCH001 line budget): binds
    the destination leaf under a `_refactored`-suffixed alias instead of
    the colliding name, and rewrites call sites to match."""
    alias_name = f"{new_name}_refactored"
    new_stmt = f"from {destination.module} import {new_name} as {alias_name}"
    record = AliasRecord(
        file_path=str(file_path),
        original_name=new_name,
        alias_name=alias_name,
        reason=(
            f"{new_name} already bound in {file_path}; call "
            f"sites rewritten to use {alias_name}"
        ),
    )
    ops = [_import_op(file_path, node, new_stmt, reason)]
    ops.extend(
        _rename_usages(
            file_path,
            source,
            tree,
            bound_as,
            alias_name,
            exclude_line=node.lineno,
        )
    )
    return ops, record


def _classify_co_imports(
    node: ast.ImportFrom, old_ref: SymbolRef, also_moving: frozenset[str]
) -> tuple[tuple[ast.alias, ...], list[ast.alias]]:
    """Split every OTHER name on `node`'s import line (besides
    `old_ref.qualname` itself) into `(sibling_aliases, real_others)` --
    `sibling_aliases` are also in `also_moving` (T-3143: co-moving in this
    same split batch, safe to fold into one rewrite) and `real_others` are
    genuinely untouched (T-3105: must still block the rewrite). Split out
    of `_handle_from_import` to keep it under the ARCH001 line budget."""
    others = [a for a in node.names if a.name != old_ref.qualname]
    sibling_aliases = tuple(a for a in others if a.name in also_moving)
    real_others = [a for a in others if a.name not in also_moving]
    return sibling_aliases, real_others


def _rewrite_reason(
    old_ref: SymbolRef, destination: SymbolRef, dest_leaf: str, sibling_aliases
) -> str:
    """The disclosed `RewriteOp.reason` text for one `_handle_from_import`
    rewrite -- names every co-moving sibling folded in alongside
    `old_ref.qualname` (T-3143), or just the single symbol when there are
    none. Split out of `_handle_from_import` to keep it under the ARCH001
    line budget."""
    if not sibling_aliases:
        return (
            f"rewrite `from {old_ref.module} import {old_ref.qualname}`"
            f" -> `from {destination.module} import {dest_leaf}`"
        )
    sibling_names = ", ".join(a.name for a in sibling_aliases)
    return (
        f"rewrite `from {old_ref.module} import "
        f"{old_ref.qualname}, {sibling_names}` -> `from "
        f"{destination.module} import ...` (same split batch, T-3143)"
    )


def _handle_from_import(
    file_path: Path,
    source: str,
    tree: ast.Module,
    node: ast.ImportFrom,
    old_ref: SymbolRef,
    destination: SymbolRef,
    dest_leaf: str,
    bound_names: set[str],
    alias_conflict: str,
    also_moving: frozenset[str] = frozenset(),
) -> tuple[list[RewriteOp], list[AliasRecord]]:
    """One `from <old module> import ...` node's rewrite: auto-alias on a
    destination-name collision, else a plain repoint. `also_moving` names
    every OTHER symbol moving to `destination.module` in the same split
    batch (T-3143) -- a co-imported name in that set is folded into ONE
    rewrite alongside the current symbol instead of blocking it, since it
    is headed to the same destination anyway; a co-imported name NOT in
    that set is still treated as genuinely untouched and blocks the
    rewrite exactly as before (T-3105). Split out of `scan_references` to
    keep it under the ARCH001 line budget."""
    ops: list[RewriteOp] = []
    aliases: list[AliasRecord] = []
    for alias in node.names:
        if alias.name != old_ref.qualname:
            continue
        bound_as = alias.asname or alias.name
        new_name = dest_leaf
        sibling_aliases, real_others = _classify_co_imports(node, old_ref, also_moving)
        if real_others:
            # This import line names the moved symbol ALONGSIDE at least
            # one GENUINELY untouched name (not part of this same split
            # batch) -- do NOT rewrite it at all. Repointing the whole
            # statement at `destination.module` would drag the untouched
            # names there too (they are not defined at the destination),
            # and it is unnecessary: the split's own re-export shim keeps
            # `old_ref.module` re-exporting the moved name, so this
            # statement stays valid unmodified (T-3105).
            continue
        reason = _rewrite_reason(old_ref, destination, dest_leaf, sibling_aliases)
        collides = (
            bound_as == old_ref.qualname
            and new_name in bound_names
            and new_name != old_ref.qualname
        )
        if collides and alias_conflict == "error":
            # Destination leaf name collides with something already bound
            # in this file's scope -- auto-alias per the design doc's
            # alias-conflict policy (default: alias the call site, never
            # rename the destination module's own namespace).
            collision_ops, record = _alias_collision_rewrite(
                file_path, source, tree, node, destination, new_name, bound_as, reason
            )
            ops.extend(collision_ops)
            aliases.append(record)
            continue
        new_stmt = _rebuild_from_import(
            node, old_ref, destination, dest_leaf, sibling_aliases
        )
        ops.append(_import_op(file_path, node, new_stmt, reason))
        if bound_as != new_name:
            ops.extend(
                _rename_usages(
                    file_path,
                    source,
                    tree,
                    bound_as,
                    new_name,
                    exclude_line=node.lineno,
                )
            )
    return ops, aliases


# frob:doc docs/commands/refactor.md#scan_references
# frob:tests tests/test_refactor.py::TestScanReferences.test_finds_from_import_call_site
# frob:tests \
# tests/test_refactor.py::TestScanReferences.test_self_import_skip_str_compare_is_not_per_node  # noqa: E501
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling so one bad file cannot abort the whole scan (a surprise becomes a disclosed 'unresolved' entry, matching this function's own never-silently-drops-it contract); no observable public-API change, so docs/commands/refactor.md needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
# frob:waive ARCH001 reason="T-1371's EXHAUST001/002 fix wraps the pre-existing per-file loop body in one try/except (AST-shape surprise -> disclosed unresolved entry, not an abort) -- boilerplate exception handling, not a new independently meaningful phase; splitting it out would just move the same lines behind an indirection"  # noqa: E501
def scan_references(
    repo_root: Path,
    resolved: ResolvedSymbol,
    destination: SymbolRef,
    alias_conflict: str = "error",
    also_moving: frozenset[str] = frozenset(),
) -> tuple[list[RewriteOp], list[AliasRecord], list[str]]:
    """Walk every `.py` file for a `from <old module> import <qualname>`
    (or `import <old module>` + attribute use) referencing the moving
    symbol, and build the exact `RewriteOp` that repoints it at
    `destination`. `also_moving` names every OTHER symbol moving to
    `destination.module` in the same split batch as `resolved` (T-3143)
    -- a shared `from <old module> import A, B` line where BOTH `A` and
    `B` are in this batch gets folded into one rewrite instead of being
    skipped as if `B` were untouched; a caller doing a single independent
    move (the default, empty set) keeps the prior T-3105 behavior
    unchanged. Returns `(ops, aliases, unresolved)`; `unresolved` names
    any call site this scan could not rewrite mechanically (a dynamic
    `getattr`/`importlib` reference, out of v1's static-AST scope) so the
    disclosed report never silently drops it.
    """
    # T-3653: lazy import, same module-cycle reason `_directives.py`'s and
    # `_prose.py`'s own lazy `module_to_path` imports already document.
    from frob.refactor._resolve import module_to_path

    ops: list[RewriteOp] = []
    aliases: list[AliasRecord] = []
    unresolved: list[str] = []
    old_ref = resolved.ref
    dest_leaf = destination.qualname.split(".")[-1]
    dest_file_path = str(module_to_path(repo_root, destination.module))

    for file_path in find_python_files(repo_root):
        if str(file_path) == resolved.file_path:
            continue
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (OSError, SyntaxError):
            continue

        try:
            bound_names = _existing_bound_names(tree)
            # T-3690 (PERF003): `file_path` is fixed for the whole inner
            # `ast.walk(tree)` loop below -- comparing it against
            # `dest_file_path` gives the identical answer on every node,
            # so hoist the O(1) comparison out here instead of repeating
            # it once per AST node (an O(n*m) nested-equality shape with
            # no per-node dependency).
            file_path_is_dest = str(file_path) == dest_file_path
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module == old_ref.module:
                    imports_moved_symbol = any(
                        alias.name == old_ref.qualname for alias in node.names
                    )
                    if imports_moved_symbol and file_path_is_dest:
                        # T-3653: this import lives in the SYMBOL'S OWN
                        # destination file -- a stale carry-forward/repoint
                        # a PRIOR move left behind, now about to become a
                        # self-import once this move lands `old_ref.
                        # qualname` locally. `_transaction.build_plan`'s
                        # own `stale_dest_import_ops` (via `_scan.
                        # stale_dest_import_ops`) already strips/rewrites
                        # this exact node; repointing it here too would
                        # target the identical line and refuse as an
                        # `OverlappingRewrites` conflict.
                        continue
                    if imports_moved_symbol and _shares_line_with_sibling_statement(
                        tree, node
                    ):
                        # A whole-span rewrite here (`_import_op`) would
                        # silently delete a semicolon-joined sibling
                        # statement on the same physical line -- refuse the
                        # mechanical rewrite and disclose instead of
                        # clobbering unrelated code.
                        unresolved.append(
                            f"{file_path}:{node.lineno}: `from {old_ref.module} "
                            "import ...` shares its physical line with another "
                            "statement (semicolon-joined) -- not rewritten "
                            "mechanically, would delete the sibling statement"
                        )
                        continue
                    new_ops, new_aliases = _handle_from_import(
                        file_path,
                        source,
                        tree,
                        node,
                        old_ref,
                        destination,
                        dest_leaf,
                        bound_names,
                        alias_conflict,
                        also_moving,
                    )
                    ops.extend(new_ops)
                    aliases.extend(new_aliases)
                elif isinstance(node, ast.Import):
                    unresolved.extend(_handle_import(file_path, tree, node, old_ref))
        except (KeyError, TypeError, ValueError) as exc:
            # This scan's own contract is a disclosed `unresolved` list,
            # never a crash for a single unusual file (this function's own
            # docstring: "never silently drops it") -- a surprising AST
            # shape in one file becomes a disclosed unresolved entry
            # instead of aborting the whole repo scan (EXHAUST001/
            # EXHAUST002, T-1371).
            unresolved.append(f"{file_path}: scan failed unexpectedly ({exc})")
        except Exception as exc:
            unresolved.append(f"{file_path}: scan failed unexpectedly ({exc})")
    return ops, aliases, unresolved


# frob:waive DUP001 reason="DUP001's r2 template match against \
# gates/__init__.py::_ticket_marker_in_diff_hunk, vet/_capability.py's \
# alias-destructure helpers, and strata/_lint.py's LINT002/005 node checks is a \
# structural coincidence: all are small filter-then-format-a-string helpers over an \
# AST-ish node, but each formats a domain-specific thing (an ImportFrom's own name \
# list here, vs. a diff hunk marker / destructure alias / lint node elsewhere) with no \
# shared behavior to extract -- the similarity is in the comprehension-then-join \
# shape, not what it computes"
def _rebuild_from_import(
    node: ast.ImportFrom,
    old_ref: SymbolRef,
    destination: SymbolRef,
    dest_leaf: str,
    also_moving_aliases: tuple[ast.alias, ...] = (),
) -> str:
    """The replacement `from <module> import <name>[, ...]` statement text
    for a `from`-import that names the moving symbol -- plus, when
    `also_moving_aliases` is given, every SIBLING symbol from the same
    split batch that was co-imported on this same line (T-3143), each
    preserving its own `as`-alias if it had one. Caller guarantees no
    genuinely untouched name remains on the line by this point
    (`_handle_from_import` already refused the rewrite otherwise)."""
    parts = [dest_leaf]
    parts.extend(
        f"{a.name} as {a.asname}" if a.asname else a.name for a in also_moving_aliases
    )
    joined = ", ".join(parts)
    return f"from {destination.module} import {joined}"


# frob:waive DUP001 reason="DUP001's r2 match against \
# gates/_docblocks.py::_doc004_violation and \
# gates/_decisions_compliance.py::_compliance005_violation is a structural \
# coincidence: all three build a small typed value from an AST node plus a couple of \
# string fields, but each builds a different result type (RewriteOp here vs. a \
# doc-block finding vs. a compliance finding) with no shared field set to extract a \
# real helper around"
def _import_op(
    file_path: Path, node: ast.ImportFrom, new_stmt: str, reason: str
) -> RewriteOp:
    """Build the `RewriteOp` replacing one `ImportFrom` statement's exact
    source span with `new_stmt`, prefixed with the original statement's
    leading whitespace (`node.col_offset`) so an indented call site --
    a function-local or block-nested import -- keeps its indentation
    instead of orphaning the following, still-indented sibling line at
    the wrong depth (T-3109: `_rebuild_from_import` returns a bare,
    unindented statement, and the replacement span must restore the
    column offset the original line had)."""
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    indented_stmt = (" " * node.col_offset) + new_stmt
    return RewriteOp(
        file_path=str(file_path),
        start_line=node.lineno,
        end_line=end,
        old_text=f"<import at line {node.lineno}>",
        new_text=indented_stmt,
        reason=reason,
    )


def _rename_usages(
    file_path: Path,
    source: str,
    tree: ast.Module,
    old_name: str,
    new_name: str,
    exclude_line: int,
) -> list[RewriteOp]:
    """Every bare-name call-site usage of `old_name` (outside the import
    statement's own line) rewritten to `new_name`, one `RewriteOp` per
    occurrence so unrelated text on the same line is untouched."""
    lines = source.splitlines()
    by_line: dict[int, list[int]] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id == old_name
            and node.lineno != exclude_line
        ):
            by_line.setdefault(node.lineno, []).append(node.col_offset)

    ops: list[RewriteOp] = []
    for lineno, cols in by_line.items():
        line_text = lines[lineno - 1]
        new_line = line_text
        # frob:waive PERF004 reason="cols is this line's own distinct column-offset \
        # list, sorted once per line so replacements apply highest-offset-first \
        # without shifting earlier offsets -- not a shared re-sort across iterations"
        for col in sorted(cols, reverse=True):
            new_line = new_line[:col] + new_name + new_line[col + len(old_name) :]
        ops.append(
            RewriteOp(
                file_path=str(file_path),
                start_line=lineno,
                end_line=lineno,
                old_text=line_text,
                new_text=new_line,
                reason=f"call-site rename {old_name} -> {new_name}",
            )
        )
    return ops

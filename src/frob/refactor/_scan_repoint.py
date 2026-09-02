import ast
from pathlib import Path

from frob.logging import get_logger
from frob.refactor._models import RewriteOp, SymbolRef
from frob.refactor._scan_carry import _names_referenced

_log = get_logger(__name__)


def _names_referenced_outside_moved_spans(
    tree: ast.Module, moved_spans: list[tuple[int, int]]
) -> set[str]:
    """Every `Name` id referenced anywhere in `tree`'s top-level
    statements EXCLUDING the ones that fall inside `moved_spans` -- a
    moved symbol's own header/body must never count as a "reference to
    itself" when checking whether a SIBLING statement left behind still
    bare-references it. Split out of `bare_name_repoint_ops` to keep it
    under the ARCH001 line budget."""
    referenced: set[str] = set()
    for node in tree.body:
        node_start = node.lineno
        node_end = node.end_lineno if node.end_lineno is not None else node_start
        if any(node_start >= start and node_end <= end for start, end in moved_spans):
            continue
        referenced |= _names_referenced(node)
    return referenced


def _bare_name_repoint_op(
    file_path: Path, hits: list[str], moved_name_map: dict[str, str], dest_module: str
) -> RewriteOp:
    """The single append `RewriteOp` `bare_name_repoint_ops` returns for
    a non-empty `hits` list -- one `from <dest_module> import ...` line
    covering every still-referenced moved name, preserving an `as`-alias
    when the destination leaf was renamed. Split out of `bare_name_
    repoint_ops` to keep it under the ARCH001 line budget."""
    parts = []
    for old in hits:
        leaf = moved_name_map[old]
        parts.append(f"{leaf} as {old}" if leaf != old else leaf)
    text = f"\nfrom {dest_module} import {', '.join(parts)}  # noqa: F401 -- T-3596\n"
    _log.info(
        "refactor.move: %s still bare-references %s after move -- adding "
        "caller-side repoint import from %s",
        file_path,
        hits,
        dest_module,
    )
    return RewriteOp(
        file_path=str(file_path),
        start_line=-1,
        end_line=-1,
        old_text="",
        new_text=text,
        reason=(
            f"caller-side bare-name repoint: {file_path} still "
            f"references {hits} after move to {dest_module}"
        ),
    )


# frob:doc docs/commands/refactor.md#bare-name-caller-side-repoint
# frob:ticket T-3596
# frob:tests \
# tests/test_refactor.py::TestGapRegressions.test_gap2_move_repoints_same_module_bare_n\
# ame_reference
def bare_name_repoint_ops(
    file_path: Path,
    moved_spans: list[tuple[int, int]],
    moved_name_map: dict[str, str],
    dest_module: str,
) -> list[RewriteOp]:
    """T-3596 gap 2: a symbol referenced only as a BARE name (no `from
    <old module> import <symbol>` statement to rewrite, because the
    reference lived in the SAME file the symbol used to live in) is
    invisible to `scan_references`, which only walks files OTHER than
    `resolved.file_path`. After the move deletes the symbol's own
    definition, any such sibling reference left in `file_path` becomes a
    plain `NameError` at call time -- exactly the "verb's own docs claim
    every call site is rewritten but a same-module one silently is not"
    gap.

    `moved_spans` is every moved symbol's own `(start_line, end_line)`
    span in `file_path`'s CURRENT (pre-apply) text -- excluded from the
    scan so the symbol's own definition is never mistaken for a
    reference to itself. `moved_name_map` maps each moved symbol's OLD
    bare name to its (possibly renamed) leaf name at `dest_module`.
    Returns at most one append `RewriteOp` targeting `file_path` with a
    `from <dest_module> import ...` line covering every moved name still
    referenced elsewhere in the file, empty if none are."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except (OSError, SyntaxError):
        return []

    referenced = _names_referenced_outside_moved_spans(tree, moved_spans)
    hits = sorted(old for old in moved_name_map if old in referenced)
    if not hits:
        return []
    return [_bare_name_repoint_op(file_path, hits, moved_name_map, dest_module)]


def _enclosing_stmt_list(tree: ast.Module, node: ast.stmt) -> list[ast.stmt] | None:
    """The one `list[ast.stmt]` (a `body`/`orelse`/`finalbody` block) that
    directly contains `node` -- i.e. `node`'s TRUE siblings, as opposed to
    the ancestor compound statements `ast.walk` also yields. Returns
    `None` if `node` is not found (should not happen for a node drawn
    from `tree` itself)."""
    for block in ast.walk(tree):
        for attr in ("body", "orelse", "finalbody"):
            # frob:waive OPAQUE001 reason="attr is drawn from the fixed literal 3-tuple above (body/orelse/finalbody), never from outside input -- equivalent to three literal attribute accesses, just looped instead of unrolled"  # noqa: E501
            stmts = getattr(block, attr, None)
            if isinstance(stmts, list) and node in stmts:
                return stmts
    return None


def _shares_line_with_sibling_statement(tree: ast.Module, node: ast.stmt) -> bool:
    """`True` iff some OTHER statement DIRECTLY SIBLING to `node` (sharing
    the same enclosing `body`/`orelse`/`finalbody` block -- never an
    ancestor compound statement) occupies the same physical source line
    as `node` (a semicolon-joined statement, `import old.module as x;
    x.y()`, being the concrete case) -- detected by checking for a
    distinct sibling node whose own `lineno` falls inside `node`'s
    `[lineno, end_lineno]` span. `_import_op` replaces the WHOLE
    `[node.lineno, node.end_lineno]` span verbatim; if a true sibling
    shares that physical line, that replacement would silently delete
    the sibling statement's own code along with the import. Callers use
    this to refuse the mechanical rewrite and fall back to `unresolved`
    instead.

    Deliberately does NOT use `ast.walk(tree)` over the whole tree: that
    yields every ancestor compound statement (`FunctionDef`, `If`,
    `Try`, ...) containing `node`, and an enclosing block's own line span
    always overlaps its body's first/last statement -- misclassifying
    every function-local or block-nested import as "semicolon-joined"
    (T-3066)."""
    siblings = _enclosing_stmt_list(tree, node)
    if siblings is None:
        return False
    end = node.end_lineno if node.end_lineno is not None else node.lineno
    for other in siblings:
        if other is node:
            continue
        other_end = other.end_lineno if other.end_lineno is not None else other.lineno
        if other.lineno <= end and node.lineno <= other_end:
            return True
    return False


def _dotted_attribute_chain(node: ast.expr) -> str | None:
    """The full dotted name an `Attribute`/`Name` chain spells out (e.g.
    `pkg.mod.greet` for `Attribute(Attribute(Name('pkg'),'mod'),'greet')`),
    or `None` if any link in the chain is not a plain `Name`/`Attribute`
    (a call result, subscript, etc. -- not a static dotted reference)."""
    parts: list[str] = []
    cur: ast.expr = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if not isinstance(cur, ast.Name):
        return None
    parts.append(cur.id)
    return ".".join(reversed(parts))


def _handle_import(
    file_path: Path, tree: ast.Module, node: ast.Import, old_ref: SymbolRef
) -> list[str]:
    """One `import <old module>` node's unresolved attribute-style
    references (`old.module.qualname(...)`) -- v1 does not mechanically
    rewrite this shape, it only flags it. Split out of `scan_references`
    to keep it under the ARCH001 line budget.

    Handles both a dotted bare import (`import pkg.mod`, usage spelled
    `pkg.mod.qualname(...)` -- the binding Python actually creates is the
    top-level package name, so the usage site re-spells the whole dotted
    path) and an aliased import (`import pkg.mod as m`, usage spelled
    `m.qualname(...)`), by comparing the FULL dotted attribute chain at
    each usage site against the expected name, not just a single `Name`
    hop -- a single-`Name`-only check would silently miss every dotted,
    non-aliased `import pkg.mod` usage."""
    unresolved: list[str] = []
    for alias in node.names:
        if alias.name != old_ref.module:
            continue
        # `import old.module` + `old.module.qualname(...)` form: the
        # module import itself does not need rewriting (its own path is
        # unchanged if only the symbol moved to a different module --
        # flag as unresolved for a human, this shape needs the
        # module-level import added/removed which v1 does not attempt
        # mechanically).
        bound_as = alias.asname or alias.name
        expected = f"{bound_as}.{old_ref.qualname}"
        for sub in ast.walk(tree):
            if not isinstance(sub, ast.Attribute):
                continue
            if _dotted_attribute_chain(sub) == expected:
                unresolved.append(
                    f"{file_path}:{sub.lineno}: `{expected}` "
                    "attribute-style reference not rewritten (v1 scans "
                    "`from ... import` call sites only)"
                )
    return unresolved

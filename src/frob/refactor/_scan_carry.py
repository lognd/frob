import ast
from pathlib import Path

from frob.logging import get_logger
from frob.refactor._models import RewriteOp

_log = get_logger(__name__)


def _top_level_import_map(tree: ast.Module, source_lines: list[str]) -> dict[str, str]:
    """Every name bound at module scope by one of `tree`'s own top-level
    `import`/`from ... import` statements, mapped to that statement's
    EXACT source text (via `source_lines`' `lineno`/`end_lineno` slice) --
    the lookup `needed_import_ops_for_symbols` uses to copy an import
    forward verbatim rather than reconstructing it (which could silently
    drop a multi-line parenthesized form or an alias)."""
    bound: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        text = "\n".join(source_lines[node.lineno - 1 : node.end_lineno])
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            bound[name] = text
    return bound


def _names_referenced(node: ast.AST) -> set[str]:
    """Every `Name` id anywhere in `node`'s subtree -- base classes,
    decorators, annotations, and nested method/function bodies all
    included, since any of them can be the reason a moved symbol needs an
    import its own header line does not show."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _names_needed_by_spans(tree: ast.Module, spans: list[tuple[int, int]]) -> set[str]:
    """Every `Name` id referenced anywhere inside the top-level statements
    of `tree` that fall within one of `spans` (a moved symbol's own
    1-indexed line range) -- the set `needed_import_ops_for_symbols`
    matches against `source_file`'s own top-level imports. Split out of
    `needed_import_ops_for_symbols` to keep it under the ARCH001 line
    budget."""
    needed: set[str] = set()
    for node in tree.body:
        node_start = getattr(node, "lineno", None)
        node_end = getattr(node, "end_lineno", None)
        if node_start is None or node_end is None:
            continue
        for start, end in spans:
            if node_start >= start and node_end <= end:
                needed |= _names_referenced(node)
                break
    return needed


def _import_texts_for_names(
    import_map: dict[str, str], needed_names: set[str]
) -> list[str]:
    """The deduplicated, declaration-ordered list of import statement
    texts in `import_map` (as built by `_top_level_import_map`) that bind
    at least one name in `needed_names` -- `import_map`'s own dict
    iteration order already matches `tree.body`'s declaration order since
    Python dicts preserve insertion order. Split out of
    `needed_import_ops_for_symbols` to keep it under the ARCH001 line
    budget."""
    seen_text: set[str] = set()
    texts: list[str] = []
    for name, text in import_map.items():
        if name not in needed_names or text in seen_text:
            continue
        seen_text.add(text)
        texts.append(text)
    return texts


def _module_level_bound_names(tree: ast.Module) -> set[str]:
    """Every name bound at `tree`'s module top level by ANY statement
    kind -- `def`/`class`, plain/annotated assignment, `import`/`from
    ... import`, and (one level deep) a `try`/`except`/`else`/`finally`
    or `if`/`else` block wrapping any of those (the `try: import msvcrt
    \\nexcept ImportError: msvcrt = None` platform-fallback shape T-3596
    gap 3 repro'd against `_lock.py`'s own `msvcrt` global). T-3122's
    `_top_level_import_map` only knows about `Import`/`ImportFrom`
    nodes; this is the wider set `needed_import_ops_for_symbols` needs to
    tell "a moved body's free variable is some OTHER still-in-source
    module global" apart from "a moved body's free variable is simply
    undefined" (a real bug the mechanical carry-forward must not paper
    over by inventing an import for it)."""
    names: set[str] = set()

    def _collect(stmts: list[ast.stmt]) -> None:
        for node in stmts:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        names.add(alias.asname or alias.name)
            elif isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            elif isinstance(node, ast.Try):
                _collect(node.body)
                for handler in node.handlers:
                    _collect(handler.body)
                _collect(node.orelse)
                _collect(node.finalbody)
            elif isinstance(node, ast.If):
                _collect(node.body)
                _collect(node.orelse)

    _collect(tree.body)
    return names


def _dest_file_top_import_block(
    dest_file: Path,
) -> tuple[int, int, set[str]] | None:
    """T-3645: `dest_file`'s own existing top-of-file import BLOCK, as
    `(start_line, end_line, statement_texts)` -- the contiguous run of
    top-level `Import`/`ImportFrom` statements starting from `tree.body`'s
    first statement (skipping only a leading module docstring), or `None`
    if `dest_file` does not exist yet or its first real statement is not
    an import. A later split/move landing a symbol in `dest_file` that
    needs its own import carried forward should MERGE into this block
    (dedup by exact statement text) rather than appending a fresh,
    scattered import statement immediately above the newly-placed symbol
    -- the ruff E402/I001 mess this ticket's own repro measured across
    every destination file a multi-symbol split populates."""
    if not dest_file.exists():
        return None
    dest_lines = dest_file.read_text(encoding="utf-8").splitlines()
    tree = ast.parse("\n".join(dest_lines), filename=str(dest_file))
    body = list(tree.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
    ):
        body = body[1:]
    texts: set[str] = set()
    start_line: int | None = None
    end_line: int | None = None
    for node in body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            break
        if start_line is None:
            start_line = node.lineno
        end_line = node.end_lineno if node.end_lineno is not None else node.lineno
        texts.add("\n".join(dest_lines[node.lineno - 1 : end_line]))
    if start_line is None or end_line is None:
        return None
    return start_line, end_line, texts


def _dest_file_bound_names(dest_file: Path) -> set[str]:
    """T-3650: every name already bound at `dest_file`'s module top level
    RIGHT NOW -- empty if `dest_file` does not exist yet. Reuses
    `_module_level_bound_names`'s own def/class/assignment/import walk
    (including its `try`/`if` one-level-deep unwrap) against `dest_
    file`'s CURRENT text, so a name a PRIOR split/move already landed
    there (as a plain def, or as a repoint import left behind by gap 2's
    `bare_name_repoint_ops`) is recognized as already-resident before
    `needed_import_ops_for_symbols` ever considers importing it back."""
    if not dest_file.exists():
        return set()
    dest_lines = dest_file.read_text(encoding="utf-8").splitlines()
    dest_tree = ast.parse("\n".join(dest_lines), filename=str(dest_file))
    return _module_level_bound_names(dest_tree)


# frob:doc docs/commands/refactor.md#split-verb-t-1201
# frob:ticket T-3122
# frob:ticket T-3596
# frob:ticket T-3650
# frob:ticket T-3645
# frob:tests \
# tests/test_refactor.py::TestRunSplit.test_split_carries_forward_imports_moved_body_needs  # noqa: E501
# frob:tests \
# tests/test_refactor.py::TestGapRegressions.test_gap3_split_carries_forward_module_level_free_variable  # noqa: E501
# frob:tests \
# tests/test_refactor.py::TestGapRegressions.test_gap1_move_carries_forward_default_arg_import  # noqa: E501
# frob:tests \
# tests/test_refactor.py::TestRunSplit.test_split_merges_carried_imports_into_existing_top_block  # noqa: E501
def needed_import_ops_for_symbols(
    source_file: Path,
    dest_file: Path,
    spans: list[tuple[int, int]],
    source_module: str | None = None,
    moving_names: frozenset[str] = frozenset(),
) -> list[RewriteOp]:
    """T-3122's fix: `build_move_ops` relocates a symbol's own source
    TEXT, but never the subset of `source_file`'s top-level imports that
    text actually references -- a moved class body naming e.g. `StrEnum`/
    `BaseModel` as a base class then lands in `dest_file` with those names
    undefined, parsing fine but raising `NameError` at real import time
    (`ast.parse` cannot see this; only a real import can).

    T-3596 gap 3 widens this: a moved body can also depend on a
    module-level NAME that is not an `import` statement at all -- a plain
    `Name = value` global, or one populated by a `try`/`except` platform
    shim (`_lock.py`'s `msvcrt`). Those are never "carried forward" (they
    are still genuinely owned by `source_file`, possibly by several
    OTHER symbols too) -- instead `dest_file` gets a synthetic `from
    <source_module> import <name>` re-import, the same mechanism the
    split verb's own re-export shim already uses for the opposite
    direction. Skips any such name already in `moving_names` (this
    chunk's OWN batch moving to `dest_file` together -- importing a name
    from its own destination file would be the T-3628 self-import defect
    this fix exists to prevent) and any name `source_file` itself does
    not bind anywhere (a genuinely undefined name is not this function's
    concern to paper over; `verify_no_undefined_names` catches that).
    `source_module=None` (the historical call shape) disables this
    synthetic-import half and keeps the original import-statement-only
    carry-forward.

    `spans` is one `(start_line, end_line)` 1-indexed pair per symbol
    being moved out of `source_file` in this chunk (a `ResolvedSymbol`'s
    own span, including any decorator lines -- T-3596 gap 4). Returns at
    most one append `RewriteOp` (`start_line=-1`) targeting `dest_file`,
    holding every needed import's exact source text plus any synthetic
    re-import line, in the source module's own declaration order,
    deduplicated -- empty if none of the moved symbols reference any of
    `source_file`'s top-level imports or other module globals.

    T-3650: `moving_names` only knows about THIS chunk's own batch --
    it says nothing about a name a PRIOR split/move already landed as a
    bare module-level def/class/assignment in `dest_file` (the T-3628
    repro: `_run_git` moved into `test_fleet_worktrees.py` in one `move`
    call, leaving a `from test_fleet_worktrees import _run_git` repoint
    import behind in `source_file` per gap 2's `bare_name_repoint_ops`;
    a LATER `split` call then finds that repoint import in `source_
    file`'s own `import_map` and would carry it straight back INTO
    `dest_file` -- a self-import). Reads `dest_file`'s CURRENT module-
    level bound names (empty set if it does not exist yet -- the common
    first-symbol-into-a-new-module case) and excludes them from both the
    import-statement and synthetic-reimport carry-forward paths, exactly
    as `moving_names` already excludes this chunk's own in-flight
    batch -- resolving within-plan references (`moving_names`) and
    already-resident destination names BEFORE ever considering an
    import."""
    source_lines = source_file.read_text(encoding="utf-8").splitlines()
    tree = ast.parse("\n".join(source_lines), filename=str(source_file))
    import_map = _top_level_import_map(tree, source_lines)
    needed_names = _names_needed_by_spans(tree, spans)
    dest_already_bound = _dest_file_bound_names(dest_file)
    carryable_names = needed_names - dest_already_bound - moving_names
    if dest_already_bound & needed_names:
        _log.info(
            "refactor.split: skipping carry-forward for name(s) %s already "
            "defined at %s (T-3650 self-import guard)",
            sorted(dest_already_bound & needed_names),
            dest_file,
        )
    needed_texts = (
        _import_texts_for_names(import_map, carryable_names) if import_map else []
    )

    synthetic_line = ""
    if source_module is not None:
        module_bound = _module_level_bound_names(tree)
        synthetic_names = sorted(
            name
            for name in carryable_names
            if name not in import_map and name in module_bound
        )
        if synthetic_names:
            synthetic_line = f"from {source_module} import {', '.join(synthetic_names)}"
            _log.info(
                "refactor.split: carrying forward module-level free "
                "variable(s) %s into %s via synthetic re-import from %s",
                synthetic_names,
                dest_file,
                source_module,
            )

    combined_texts = list(needed_texts)
    if synthetic_line:
        combined_texts.append(synthetic_line)
    return _carry_forward_ops_for_texts(dest_file, combined_texts)


def _carry_forward_ops_for_texts(
    dest_file: Path, combined_texts: list[str]
) -> list[RewriteOp]:
    """`needed_import_ops_for_symbols`'s own final step, split out (
    ARCH001): turn its already-computed `combined_texts` (needed
    top-level imports plus any synthetic free-variable re-import) into
    the actual `RewriteOp`(s) against `dest_file`.

    T-3645: a destination file that ALREADY HAS its own top-of-file
    import block (i.e. this is not the first symbol landing there) gets
    the new import(s) merged INTO that block -- deduped by exact
    statement text, appended after the block's own last line -- instead
    of a fresh append-at-file-end statement landing immediately above
    THIS symbol's own newly-appended body. Each subsequent split/move
    into the same destination keeps growing the same one block rather
    than scattering a new one per call; `ruff --fix` sorts/dedupes the
    result same as it always has, this only stops the ruff E402/I001
    mess of import statements interleaved with class/function bodies."""
    if not combined_texts:
        return []

    top_block = _dest_file_top_import_block(dest_file)
    if top_block is not None:
        block_start, block_end, existing_texts = top_block
        merge_texts = [t for t in combined_texts if t not in existing_texts]
        if not merge_texts:
            return []
        dest_lines = dest_file.read_text(encoding="utf-8").splitlines()
        block_text = "\n".join(dest_lines[block_start - 1 : block_end])
        merged = block_text + "\n" + "\n".join(merge_texts)
        _log.info(
            "refactor.split: merging %d import statement(s) into %s's own "
            "existing top-of-file import block",
            len(merge_texts),
            dest_file,
        )
        return [
            RewriteOp(
                file_path=str(dest_file),
                start_line=block_start,
                end_line=block_end,
                old_text=block_text,
                new_text=merged,
                reason=f"merge import(s) needed by symbol(s) moved into "
                f"{dest_file}'s own existing top-of-file import block",
            )
        ]

    _log.info(
        "refactor.split: carrying forward %d import statement(s) into %s",
        len(combined_texts),
        dest_file,
    )
    combined = "\n".join(combined_texts) + "\n\n"
    return [
        RewriteOp(
            file_path=str(dest_file),
            start_line=-1,
            end_line=-1,
            old_text="",
            new_text=combined,
            reason=f"carry forward import(s) needed by symbol(s) moved into "
            f"{dest_file}",
        )
    ]


# T-3690 (PERF004): `stale_dest_import_ops` used to call `sorted()` twice
# over the SAME per-node list (once for the log line, once for the
# `RewriteOp.reason`) -- sort once here and let both call sites share it.
# frob:waive PERF004 reason="stale is this node's own distinct per-import-statement \
# name set (1-2 entries), not a shared re-sort -- same posture as every other \
# per-key-distinct-set PERF004 waiver in this codebase"
def _sorted_stale_names(stale: list[ast.alias]) -> list[str]:
    """The deterministic, deduplicated-sort name list for one stale-import
    node's `moving_names` overlap -- shared by `stale_dest_import_ops`'s
    log line and its `RewriteOp.reason` so they sort the same data once,
    not twice."""
    return sorted(a.asname or a.name for a in stale)


# frob:doc docs/commands/refactor.md#split-verb-t-1201
# frob:ticket T-3653
# frob:ticket T-3690
# frob:tests \
# tests/test_refactor.py::TestGapRegressions.test_gap5_stale_dest_import_becomes_circular_when_its_own_symbol_later_moves_in  # noqa: E501
# frob:tests \
# tests/test_refactor.py::TestGapRegressions.test_stale_dest_import_ops_sorts_each_stale_set_once  # noqa: E501
# frob:waive AFFECT001 reason="T-3690 only dedups an internal sorted() call (log line \
# + RewriteOp.reason now share one sort) -- no observable public-API or output change, \
# so docs/commands/refactor.md needs no update"
def stale_dest_import_ops(
    dest_file: Path, moving_names: frozenset[str]
) -> list[RewriteOp]:
    """T-3653: `needed_import_ops_for_symbols`/T-3650 only ever guard a
    NEW carry-forward import from self-importing a name already resident
    at `dest_file` -- neither one revisits an EXISTING top-level import
    statement a PRIOR split/move already wrote into `dest_file`, when the
    name that OLD import references is `moving_names` (this call's own
    batch, about to be newly DEFINED at `dest_file`'s own top level).
    Left alone, `dest_file` ends up both importing a name from its old
    source module AND defining it locally -- a genuine `ImportError`
    (partially initialized module) at real import time, which `apply_
    plan`'s Verify phase catches and rolls back, but which this function
    exists to prevent from ever being attempted.

    Returns one `RewriteOp` per stale `ImportFrom` statement touched:
    the statement's exact span rewritten with `moving_names` stripped
    from its alias list (preserving every other name's own `as`-alias),
    or deleted outright (`new_text=""`) if stripping empties it. Empty
    list if `dest_file` does not exist yet, or none of its own top-level
    imports name anything in `moving_names`."""
    if not dest_file.exists():
        return []
    dest_lines = dest_file.read_text(encoding="utf-8").splitlines()
    dest_tree = ast.parse("\n".join(dest_lines), filename=str(dest_file))
    ops: list[RewriteOp] = []
    for node in dest_tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        stale = [a for a in node.names if (a.asname or a.name) in moving_names]
        if not stale:
            continue
        keep = [a for a in node.names if (a.asname or a.name) not in moving_names]
        end = node.end_lineno if node.end_lineno is not None else node.lineno
        if keep:
            names_text = ", ".join(
                f"{a.name} as {a.asname}" if a.asname else a.name for a in keep
            )
            module_text = ("." * node.level) + (node.module or "")
            new_stmt = (
                " " * node.col_offset
            ) + f"from {module_text} import {names_text}"
        else:
            new_stmt = ""
        sorted_stale = _sorted_stale_names(stale)
        _log.info(
            "refactor.split: stripping stale carry-forward name(s) %s from "
            "%s's own existing import at line %d (T-3653 self-import guard)",
            sorted_stale,
            dest_file,
            node.lineno,
        )
        ops.append(
            RewriteOp(
                file_path=str(dest_file),
                start_line=node.lineno,
                end_line=end,
                old_text=f"<import at line {node.lineno}>",
                new_text=new_stmt,
                reason=f"strip stale carry-forward import of {sorted_stale} now defined locally",  # noqa: E501
            )
        )
    return ops

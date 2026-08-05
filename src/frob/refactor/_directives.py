"""Directive/waiver carrier (T-1199, absorbs T-1134): when a refactor moves
a symbol, its `frob:*` comment-DSL directives and waivers move/repoint with
it (docs/design/refactor-verb.md's reference-kind inventory, "frob:*
directive targets" and "waivers" rows).

Three carried reference kinds, matching the epic's acceptance:

1. A `frob:waive`/`frob:*` directive comment block physically attached
   directly above the moving symbol's own definition line: extends the
   move span so it relocates WITH the symbol's code (`extend_span_for_
   attached_directives`), rather than being left behind at the old file
   (the symbol's own AST span never includes its leading comments).
2. A `frob:*` directive anywhere else in the repo whose TARGET or SRC
   string names the moving symbol (its `path::qualname` symref form):
   rewritten in place to the new symref, reusing `frob.graph.dsl`'s
   existing directive parser rather than a second regex
   (`scan_directive_carriers`).
3. A `frob.lock` ack entry keyed on the moving symbol's old symref:
   re-keyed to the new symref, carried forward rather than reported stale
   by DRIFT001 (`carry_lock_acks`).
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from frob.graph.dsl import parse_directives
from frob.graph.lock import load_lock, write_lock
from frob.lang import parse_file
from frob.logging import get_logger
from frob.refactor._models import ResolvedSymbol, RewriteOp, SymbolRef
from frob.refactor._scan import find_python_files

_log = get_logger(__name__)

__all__ = [
    "carry_lock_acks",
    "extend_span_for_attached_directives",
    "scan_directive_carriers",
]


def _display_path(path: Path) -> str:
    """Repo-relative POSIX path when possible, else the path as given --
    mirrors `frob.lang._display_path` exactly (private there, so this
    module keeps its own copy rather than importing a name that is not
    part of `frob.lang`'s public surface) since a `frob:*` directive's
    `target`/`src` symref is built from THAT path convention; a mismatched
    convention here would silently never match a real directive."""
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        return path.as_posix()


# frob:doc docs/commands/refactor.md#extend_span_for_attached_directives
# frob:tests tests/test_refactor.py::TestDirectiveCarrier.test_attached_waiver_moves_with_symbol  # noqa: E501
def extend_span_for_attached_directives(
    source_lines: Sequence[str], start_line: int
) -> int:
    """The new (lower) start line to use for a move op so a contiguous
    block of `#`-comment lines directly above `start_line` (no blank-line
    gap) that contains at least one `frob:` directive moves WITH the
    symbol's own code, instead of being left behind at the old file --
    `ast`'s own `lineno`/`end_lineno` for a def/class never includes its
    leading comment lines, so the Apply phase's move span needs this
    explicit extension. Returns `start_line` unchanged if nothing
    attached qualifies (an unrelated comment, or no comment at all)."""
    idx = start_line - 2  # 0-indexed line directly above start_line
    block_start = start_line
    saw_directive = False
    while idx >= 0:
        line = source_lines[idx].strip()
        if not line.startswith("#"):
            break
        if "frob:" in line:
            saw_directive = True
        block_start = idx + 1
        idx -= 1
    return block_start if saw_directive else start_line


# frob:doc docs/commands/refactor.md#scan_directive_carriers
# frob:tests tests/test_refactor.py::TestDirectiveCarrier.test_directive_target_elsewhere_rewritten  # noqa: E501
def scan_directive_carriers(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> tuple[list[RewriteOp], list[str]]:
    """Repo-wide scan (Plan phase): every `frob:*` directive whose `target`
    or `src` names the moving symbol, in either its `path::qualname` symref
    form or its dotted-module form, gets a `RewriteOp` repointing it at the
    destination's equivalent form. Reuses `frob.graph.dsl.parse_directives`
    (the same parser every gate reads) rather than a second regex, per
    the ticket's own design note. Returns `(ops, unresolved)`; a directive
    whose comment span cannot be re-read for any reason is disclosed in
    `unresolved`, never silently dropped."""
    # `destination`'s own file path is computed the same way `_resolve.py`'s
    # `module_to_path` computes it; imported lazily to avoid a module-level
    # import cycle between `_resolve` and this module.
    from frob.refactor._resolve import module_to_path

    old_rel = _display_path(Path(resolved.file_path))
    dest_rel = _display_path(module_to_path(repo_root, destination.module))
    old_symref = f"{old_rel}::{resolved.ref.qualname}"
    new_symref = f"{dest_rel}::{destination.qualname.split('.')[-1]}"
    old_dotted = resolved.ref.dotted
    new_dotted = destination.dotted
    rewrite_map = {old_symref: new_symref, old_dotted: new_dotted}

    ops: list[RewriteOp] = []
    unresolved: list[str] = []
    for file_path in find_python_files(repo_root):
        if str(file_path) == resolved.file_path:
            # The moving symbol's own file is handled by the move ops
            # themselves (any directive physically attached moves via
            # `extend_span_for_attached_directives`); scanning it again
            # here would double-rewrite the same comment.
            continue
        file_ops, file_unresolved = _scan_file_for_directive_carriers(
            file_path, rewrite_map
        )
        ops.extend(file_ops)
        unresolved.extend(file_unresolved)
    return ops, unresolved


def _scan_file_for_directive_carriers(
    file_path: Path, rewrite_map: dict[str, str]
) -> tuple[list[RewriteOp], list[str]]:
    """One file's worth of `scan_directive_carriers` work: parse it,
    find every `frob:*` directive edge whose target/src matches a key in
    `rewrite_map`, and turn each match into a `RewriteOp` (or an
    `unresolved` entry if the literal text cannot be located). Split out
    of `scan_directive_carriers` so the repo-wide loop there stays a thin
    dispatch over this per-file unit."""
    ops: list[RewriteOp] = []
    unresolved: list[str] = []
    parsed_result = parse_file(file_path)
    if parsed_result.is_err:
        return ops, unresolved
    parsed = parsed_result.danger_ok
    try:
        edges, _malformed = parse_directives(parsed)
    except (KeyError, TypeError, ValueError) as exc:
        unresolved.append(f"{file_path}: directive scan failed ({exc})")
        return ops, unresolved
    source_lines = file_path.read_text(encoding="utf-8").splitlines()
    seen_spans: set[tuple[int, int]] = set()
    for edge in edges:
        hit_old, hit_new = None, None
        if edge.target in rewrite_map:
            hit_old, hit_new = edge.target, rewrite_map[edge.target]
        elif edge.src in rewrite_map:
            hit_old, hit_new = edge.src, rewrite_map[edge.src]
        if hit_old is None or hit_new is None:
            continue
        span = _comment_span_for_edge(parsed, edge)
        if span is None or span in seen_spans:
            continue
        seen_spans.add(span)
        start, end = span
        old_text = "\n".join(source_lines[start - 1 : end])
        if hit_old not in old_text:
            unresolved.append(
                f"{file_path}:{start}: directive names {hit_old!r} but the "
                "literal text could not be located for rewrite"
            )
            continue
        new_text = old_text.replace(hit_old, hit_new)
        ops.append(
            RewriteOp(
                file_path=str(file_path),
                start_line=start,
                end_line=end,
                old_text=old_text,
                new_text=new_text,
                reason=f"carry frob:{edge.kind.value} directive {hit_old} -> {hit_new}",
            )
        )
    return ops, unresolved


def _comment_span_for_edge(parsed, edge) -> tuple[int, int] | None:
    """The `(start_line, end_line)` of whichever `RawComment` produced
    `edge` -- matched by `origin` (the comment's own repr, per
    `frob.graph.dsl`'s per-line edge construction) against `parsed.
    comments`' spans; `None` if no comment in `parsed` matches (a
    synthesized edge, e.g. an inferred protocol transition, that has no
    single source comment span of its own)."""
    for comment in parsed.comments:
        if edge.origin == f"{parsed.path}:{comment.span[0]}":
            return comment.span
    return None


# frob:doc docs/commands/refactor.md#carry_lock_acks
# frob:tests tests/test_refactor.py::TestDirectiveCarrier.test_lock_ack_carried_to_new_symref  # noqa: E501
def carry_lock_acks(
    repo_root: Path, resolved: ResolvedSymbol, destination: SymbolRef
) -> int:
    """Post-apply step: re-key every `frob.lock` entry whose `ref` names
    the moving symbol's old symref to its new one, so an unchanged digest
    is never reported stale by DRIFT001 just because the symbol moved.
    Returns the number of entries carried (0 if `frob.lock` does not exist
    or holds no matching entry -- both are the normal, non-error case)."""
    from frob.refactor._resolve import module_to_path

    lock_path = repo_root / "frob.lock"
    lock_result = load_lock(lock_path)
    if lock_result.is_err:
        _log.warning("refactor.directives: frob.lock unreadable, skipping ack carry")
        return 0
    lock = lock_result.danger_ok
    old_symref = f"{_display_path(Path(resolved.file_path))}::{resolved.ref.qualname}"
    dest_rel = _display_path(module_to_path(repo_root, destination.module))
    new_symref = f"{dest_rel}::{destination.qualname.split('.')[-1]}"

    carried = 0
    new_entries = []
    for entry in lock.entries:
        if entry.ref == old_symref:
            new_entries.append(entry.model_copy(update={"ref": new_symref}))
            carried += 1
        else:
            new_entries.append(entry)
    if carried == 0:
        return 0
    new_lock = lock.model_copy(update={"entries": tuple(new_entries)})
    write_result = write_lock(new_lock, lock_path)
    if write_result.is_err:
        _log.warning("refactor.directives: failed writing carried frob.lock acks")
        return 0
    _log.info(
        "refactor.directives: carried %d frob.lock ack(s) %s -> %s",
        carried,
        old_symref,
        new_symref,
    )
    return carried

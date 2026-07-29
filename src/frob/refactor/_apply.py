"""Apply phase: execute a computed `RefactorPlan` against the filesystem
(docs/design/refactor-verb.md's Transaction model, step 3).

Every rewrite in the plan was already computed in the Plan phase; this
module only splices exact spans, never re-derives what to rewrite --
matching the design doc's "the plan is computed once, applied once" rule.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.logging import get_logger
from frob.refactor._models import RefactorError, RefactorPlan, RewriteOp
from frob.refactor._resolve import module_to_path

_log = get_logger(__name__)

__all__ = ["apply_plan", "build_move_ops"]


# frob:doc docs/commands/refactor.md#build_move_ops
# frob:tests tests/test_refactor.py::TestBuildMoveOps.test_build_move_ops_deletes_and_appends  # noqa: E501
def build_move_ops(
    repo_root: Path,
    plan_source_file: str,
    start_line: int,
    end_line: int,
    dest_module: str,
    new_name: str,
    old_name: str,
) -> tuple[RewriteOp, RewriteOp]:
    """Compute the two `RewriteOp`s that relocate a symbol's own source
    span: delete it from the old file, append it (renamed if needed) to
    the destination file. Kept as a free function so `_transaction.py`'s
    plan-building can call it without importing apply-phase internals
    directly.
    """
    old_path = Path(plan_source_file)
    old_lines = old_path.read_text(encoding="utf-8").splitlines()
    body = "\n".join(old_lines[start_line - 1 : end_line])
    if new_name != old_name:
        # Best-effort rename of the `def <old_name>`/`class <old_name>`
        # header line only -- the plan's own reference_ops handle every
        # external call site; this only needs the definition's own header
        # to match its new qualname.
        body_lines = body.splitlines()
        if body_lines:
            body_lines[0] = body_lines[0].replace(old_name, new_name, 1)
        body = "\n".join(body_lines)

    delete_op = RewriteOp(
        file_path=str(old_path),
        start_line=start_line,
        end_line=end_line,
        old_text=body,
        new_text="",
        reason=f"move {old_name} out of {old_path}",
    )

    dest_path = module_to_path(repo_root, dest_module)
    dest_exists = dest_path.is_file()
    insert_marker = "\n\n" + body + "\n" if dest_exists else body + "\n"
    append_op = RewriteOp(
        file_path=str(dest_path),
        start_line=-1,
        end_line=-1,
        old_text="",
        new_text=insert_marker,
        reason=f"insert {new_name} into {dest_path}",
    )
    return delete_op, append_op


# frob:doc docs/commands/refactor.md#build_move_ops
# frob:tests tests/test_refactor.py::TestApplyPlan.test_overlapping_ops_refuse_before_write  # noqa: E501
def _find_overlapping_ops(
    ops: list[RewriteOp],
) -> tuple[RewriteOp, RewriteOp] | None:
    """The first pair of line-span ops (`start_line != -1`) in `ops` whose
    `[start_line, end_line]` ranges intersect (inclusive), or `None` if
    none do. Two ops sharing or overlapping a line range both computed
    against the ORIGINAL source is exactly the silent-clobber hazard: the
    second one applied (per `_apply_ops_to_file`'s highest-line-first
    order) would splice its own replacement text over the span the first
    op already claimed, discarding the first op's rewrite with no
    warning -- this is the plan/apply-time check that refuses instead."""
    spans = [op for op in ops if op.start_line != -1]
    for i, a in enumerate(spans):
        for b in spans[i + 1 :]:
            if a.start_line <= b.end_line and b.start_line <= a.end_line:
                return a, b
    return None


def _apply_ops_to_file(file_path: Path, ops: list[RewriteOp]) -> None:
    """Splice every op targeting one file in a single pass: appends
    (`start_line == -1`) go to the end in declared order; line-span
    replacements apply highest-line-first so an earlier op's line shift
    never invalidates a later op's line numbers."""
    appends = [op for op in ops if op.start_line == -1]
    spans = sorted(
        (op for op in ops if op.start_line != -1),
        key=lambda op: op.start_line,
        reverse=True,
    )

    if file_path.is_file():
        lines = file_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    for op in spans:
        replacement = op.new_text.splitlines() if op.new_text else []
        lines[op.start_line - 1 : op.end_line] = replacement

    text = "\n".join(lines)
    if lines:
        text += "\n"
    for op in appends:
        text += op.new_text

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(text, encoding="utf-8")


# frob:doc docs/commands/refactor.md#apply_plan
# frob:tests tests/test_refactor.py::TestApplyPlan.test_apply_then_rollback_restores_tree  # noqa: E501
def apply_plan(repo_root: Path, plan: RefactorPlan) -> Result[None, RefactorError]:
    """Splice every `RewriteOp` in `plan.all_ops` into its target file.
    Groups ops per file first so a file touched by both a move-op and
    several reference-ops gets exactly one rewritten version, not one
    write per op.

    Refuses with `Err(OverlappingRewrites)`, before a single byte is
    written, if any two line-span ops targeting the same file overlap or
    share a line range -- see `_find_overlapping_ops`'s docstring for why
    this specific hazard (two ops each computed against the ORIGINAL
    source, one silently clobbering the other on apply) cannot be allowed
    through."""
    by_file: dict[str, list[RewriteOp]] = {}
    for op in plan.all_ops:
        by_file.setdefault(op.file_path, []).append(op)

    for file_path_str, ops in by_file.items():
        overlap = _find_overlapping_ops(ops)
        if overlap is not None:
            a, b = overlap
            _log.error(
                "refactor.apply: refusing -- overlapping rewrites in %s: "
                "[%d-%d] (%s) overlaps [%d-%d] (%s)",
                file_path_str,
                a.start_line,
                a.end_line,
                a.reason,
                b.start_line,
                b.end_line,
                b.reason,
            )
            return Err(RefactorError.OverlappingRewrites)

    try:
        for file_path_str, ops in by_file.items():
            _apply_ops_to_file(Path(file_path_str), ops)
    except OSError as exc:
        _log.error("refactor.apply: failed writing during apply: %s", exc)
        return Err(RefactorError.ApplyFailed)

    _log.info(
        "refactor.apply: applied %d op(s) across %d file(s)",
        len(plan.all_ops),
        len(by_file),
    )
    return Ok(None)

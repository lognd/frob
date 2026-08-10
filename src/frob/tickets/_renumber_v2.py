"""
frob.tickets._renumber_v2 -- the v2-mode `renumber_one` backend (design
section 4.1): `git mv tickets/<old> tickets/<new>` plus per-ticket-file
reference rewrite, in place of `_new_renumber`'s whole-ledger
read-modify-write.
(LARGE001 residue split of `frob.tickets._new_renumber`, T-1420: carved out
verbatim with its T-1255 directives intact -- `renumber_one` in
`_new_renumber.py` still dispatches to `renumber_one_v2` here for a v2-mode
repo, imported back by name.)
"""

from __future__ import annotations

import re
from contextlib import ExitStack
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._leases import rename_lease
from frob.tickets._models import RenumberReport, TicketError
from frob.tickets._new_renumber import (
    _log_renumber_done,
    _log_renumber_dry_run,
    _refuse_if_other_worktree_holds_live_lease_for_id,
    _rewrite_body_prose_references,
    _scan_code_references,
)
from frob.tickets._store import atomic_write, ticket_lock, tickets_dir
from frob.tickets._worktree_guard import enforce_worktree_lease

# Shared "frob.tickets" logger name kept explicit (not get_logger(__name__),
# which would read "frob.tickets._renumber_v2") -- matches
# `_new_renumber.py`'s own reasoning (T-1089 lineage) so caplog filters by
# the package logger name keep working across this split.
_log = get_logger("frob.tickets")


_V2_ID_FRONTMATTER_RE = re.compile(r"(?m)^id:\s*\S+")


def _v2_id_dir(root: Path, ticket_id: str) -> Path | None:
    """The v2 ticket directory (active `tickets/<id>/` or archived
    `tickets/archive/<id>/`) currently holding `ticket_id`'s `ticket.md`, or
    `None` if neither exists -- the v2-mode analog of
    `_load_and_validate_renumber_ids`'s active/archive membership check."""
    from frob.tickets._store import v2_ticket_dir

    active = v2_ticket_dir(root, ticket_id)
    if (active / "ticket.md").is_file():
        return active
    archived = tickets_dir(root) / "archive" / ticket_id
    if (archived / "ticket.md").is_file():
        return archived
    return None


def _rewrite_v2_id_field(text: str, new_id: str) -> str:
    """Rewrite a v2 `ticket.md`'s frontmatter `id:` line to `new_id` (design
    section 4.1 step 3) -- the one field a `git mv` does not fix up on its
    own, since the directory name and the frontmatter `id:` are two
    independent pieces of data that must both move together."""
    return _V2_ID_FRONTMATTER_RE.sub(f"id: {new_id}", text, count=1)


# frob:ticket T-1504
def _v2_reference_files(root: Path) -> list[Path]:
    """Every `ticket.md`/`done-report.md` under `tickets/` (active or
    archived), sorted -- the multi-file glob design section 4.1 step 4 scans
    for whole-word prose citations of a renumbered id, generalizing
    `_rewrite_body_prose_references`'s single-ledger-body scan to a glob over
    disjoint per-ticket files."""
    d = tickets_dir(root)
    if not d.exists():
        return []
    # frob:waive WALK001 reason="d is the tickets/ dir alone -- a small, bounded-scope \
    # subtree (ticket.md/done-report.md files only) with no nested \
    # .git/.venv/node_modules/build/dist/target to prune, matching the gate's own \
    # small-bounded-walk escape hatch"
    return sorted(p for p in d.rglob("*.md") if p.is_file())


def _scan_v2_reference_files(
    root: Path, old_id: str, new_id: str, *, exclude: Path
) -> dict[Path, tuple[str, int]]:
    """Every `tickets/**/*.md` file (other than `exclude`, the renamed
    ticket's own `ticket.md`) whose text whole-word-cites `old_id`, mapped to
    its rewritten text and hit count -- reuses
    `_rewrite_body_prose_references`'s single-pair matching core (a
    `{old_id: new_id}` mapping of one entry) so both call sites share the
    exact same whole-word regex semantics."""
    id_mapping = {old_id: new_id}
    changed: dict[Path, tuple[str, int]] = {}
    for path in _v2_reference_files(root):
        if path == exclude:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if old_id not in text:
            continue
        try:
            rewritten, hits = _rewrite_body_prose_references(text, id_mapping)
        except Exception:
            # One file's prose confusing the rewrite core must not abort
            # the whole v2-reference scan over every OTHER file
            # (EXHAUST001/EXHAUST002, T-1371) -- skip just this one, same
            # as the read-failure branch above.
            continue
        if hits:
            changed[path] = (rewritten, hits)
    return changed


def _git_mv_ticket_dir(
    root: Path, old_dir: Path, new_dir: Path
) -> Result[None, TicketError]:
    """`git mv old_dir new_dir` (design section 4.1 step 2) -- falls back to
    a plain filesystem rename if `old_dir` is not yet tracked by git (e.g. a
    just-filed draft that has not been `git add`ed), since a git-mv over an
    untracked path always fails even though the rename itself is perfectly
    safe.

    Chain-review fix (mirrors `frob.tickets._store.git_mv_dir`'s identical
    fix, found alongside T-1258): `git mv` on a directory refuses with "No
    such file or directory" whenever `new_dir`'s PARENT does not exist yet,
    which used to silently take the os.rename fallback below -- losing the
    real git rename record for what is actually the common case (a fresh
    id range's first renumber into it), not just the rare untracked-draft
    case. Pre-creating the parent here makes `git mv` itself succeed (and
    record a real rename) for every case except a genuinely untracked
    source."""
    new_dir.parent.mkdir(parents=True, exist_ok=True)
    argv = ("git", "-C", str(root), "mv", str(old_dir), str(new_dir))
    spawned = run_argv(argv)
    if spawned.is_ok and spawned.danger_ok.returncode == 0:
        return Ok(None)
    _log.debug(
        "tickets: git mv %s -> %s failed or untracked, falling back to os.rename",
        old_dir,
        new_dir,
    )
    try:
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        old_dir.rename(new_dir)
    except OSError as exc:
        _log.error(
            "tickets: renumber_one_v2: rename %s -> %s failed: %s",
            old_dir,
            new_dir,
            exc,
        )
        return Err(TicketError.WriteFailed)
    return Ok(None)


# frob:ticket T-1255
def _validate_v2_renumber_ids(
    root: Path, old_id: str, new_id: str
) -> Result[Path, TicketError]:
    """Validate `old_id`/`new_id` are v2-renumber-able (not equal, `old_id`
    resolves to a real v2 ticket dir, `new_id` free), returning `old_id`'s
    directory on success -- the v2 analog of
    `_load_and_validate_renumber_ids`."""
    if old_id == new_id:
        _log.warning("tickets: renumber_one_v2 %s -> %s is a no-op id", old_id, new_id)
        return Err(TicketError.InvalidTransition)
    old_dir = _v2_id_dir(root, old_id)
    if old_dir is None:
        _log.error("tickets: renumber_one_v2: %s not found", old_id)
        return Err(TicketError.NotFound)
    if _v2_id_dir(root, new_id) is not None:
        _log.error("tickets: renumber_one_v2: target id %s already exists", new_id)
        return Err(TicketError.DuplicateId)
    return Ok(old_dir)


# frob:ticket T-1255
def _build_v2_renumber_report(
    root: Path,
    old_id: str,
    new_id: str,
    old_dir: Path,
    ref_changes: dict[Path, tuple[str, int]],
    code_changes: dict[Path, tuple[str, int]],
    dry_run: bool,
) -> RenumberReport:
    """Assemble the `RenumberReport` for a v2-mode rename, from the computed
    reference-file/code-reference scan results plus the renamed ticket's own
    `id:` field rewrite."""
    occurrences = (
        sum(hits for _text, hits in ref_changes.values())
        + sum(hits for _text, hits in code_changes.values())
        + 1  # the renamed ticket's own id: field
    )
    files_changed = sorted(
        {str(p.relative_to(root)) for p in (*ref_changes, *code_changes)}
        | {str((old_dir.parent / new_id).relative_to(root) / "ticket.md")}
    )
    return RenumberReport(
        old_id=old_id,
        new_id=new_id,
        ledger_changed=True,
        files_changed=tuple(files_changed),
        occurrences=occurrences,
        dry_run=dry_run,
    )


# frob:ticket T-1255
def _persist_v2_renumber(
    root: Path,
    old_dir: Path,
    new_id: str,
    new_text: str,
    ref_changes: dict[Path, tuple[str, int]],
    code_changes: dict[Path, tuple[str, int]],
) -> Result[Path, TicketError]:
    """`git mv` `old_dir` to its new id, write back the moved `ticket.md`
    plus every rewritten reference/code file, returning the new directory on
    success. A reference file that lived INSIDE `old_dir` (e.g. the moved
    ticket's own `done-report.md`) is written under the NEW directory
    instead -- every other reference file's path is untouched by the mv."""
    new_dir = old_dir.parent / new_id
    moved = _git_mv_ticket_dir(root, old_dir, new_dir)
    if moved.is_err:
        return Err(moved.danger_err)
    written = atomic_write(new_dir / "ticket.md", new_text)
    if written.is_err:
        return Err(written.danger_err)
    for path, (rewritten, _hits) in {**ref_changes, **code_changes}.items():
        target = (
            new_dir / path.relative_to(old_dir)
            if path in ref_changes and path.is_relative_to(old_dir)
            else path
        )
        write_result = atomic_write(target, rewritten)
        if write_result.is_err:
            return Err(write_result.danger_err)
    return Ok(new_dir)


# frob:doc docs/design/ledger-v2.md#41-renumber-with-reference-rewrite
# frob:ticket T-1255
# frob:ticket T-1882
# frob:ticket T-1918
# frob:waive AFFECT001 reason="T-1882/T-1918 only adjust the live-lease refusal guard \
# (_refuse_if_other_worktree_holds_live_lease_for_id) ahead of the existing rename \
# steps this function's design doc section already walks through -- no change to the \
# rename mechanism itself; docs/design/ledger-v2.md is also out of this ticket's \
# declared scope (src/frob/app/ticket_runner/_query.py, \
# src/frob/tickets/_renumber_v2.py, src/frob/tickets/_new_renumber.py)"
# frob:tests tests/test_tickets_collision.py::TestRenumberOneV2.test_git_mv_renames_directory_and_rewrites_id_field  # noqa: E501
# frob:tests tests/test_tickets_collision.py::TestRenumberOneV2.test_sibling_ticket_prose_citation_rewritten  # noqa: E501
# frob:tests tests/test_tickets_collision.py::TestRenumberOneV2.test_locks_acquired_in_sorted_id_order_no_deadlock  # noqa: E501
def renumber_one_v2(
    root: Path, old_id: str, new_id: str, *, dry_run: bool = False
) -> Result[RenumberReport, TicketError]:
    """v2-mode `renumber_one` (design section 4.1): `git mv tickets/<old>
    tickets/<new>` (or `tickets/archive/<old>` if archived), rewrite the
    moved `ticket.md`'s own `id:` frontmatter field, then rewrite every OTHER
    `tickets/**/*.md` file's whole-word prose citation of `old_id` -- reusing
    `_rewrite_body_prose_references`'s matching core verbatim, just re-
    pointed at a multi-file glob instead of one ledger's rendered text.

    Locks are acquired for BOTH `old_id` and `new_id` in sorted order (design
    section 3's fixed-order discipline, mirroring the T-1090 lesson this
    generalizes) so a renumber can never lock-order-deadlock against a
    concurrent renumber/write touching the same two ids in the opposite
    order. A `dry_run` call takes no locks and mutates nothing -- it only
    computes and reports what WOULD change."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    if not dry_run:
        # T-1918 (was T-1882's all-ids guard): refuse only while a live
        # foreign lease names THIS SPECIFIC old_id -- a dry-run mutates
        # nothing so it stays exempt, matching `renumber`/`renumber_one`'s
        # own posture. See `_refuse_if_other_worktree_holds_live_lease_
        # for_id`'s docstring for why the bulk-path guard is too broad for
        # a single-id rename (draft promotion in particular).
        lease_conflict = _refuse_if_other_worktree_holds_live_lease_for_id(
            root, old_id
        )
        if lease_conflict.is_err:
            return Err(lease_conflict.danger_err)
    validated = _validate_v2_renumber_ids(root, old_id, new_id)
    if validated.is_err:
        return Err(validated.danger_err)
    old_dir = validated.danger_ok

    lock_ids = sorted({old_id, new_id})
    with ExitStack() as stack:
        for lock_id in lock_ids:
            stack.enter_context(ticket_lock(root, lock_id))

        ticket_path = old_dir / "ticket.md"
        old_text = ticket_path.read_text(encoding="utf-8")
        new_text = _rewrite_v2_id_field(old_text, new_id)
        ref_changes = _scan_v2_reference_files(
            root, old_id, new_id, exclude=ticket_path
        )
        code_changes = _scan_code_references(root, old_id, new_id)
        report = _build_v2_renumber_report(
            root, old_id, new_id, old_dir, ref_changes, code_changes, dry_run
        )
        if dry_run:
            _log_renumber_dry_run(old_id, new_id, report)
            return Ok(report)

        persisted = _persist_v2_renumber(
            root, old_dir, new_id, new_text, ref_changes, code_changes
        )
        if persisted.is_err:
            return Err(persisted.danger_err)

    rename_lease(root, old_id, new_id)
    _log_renumber_done(old_id, new_id, {**ref_changes, **code_changes}, report)
    return Ok(report)

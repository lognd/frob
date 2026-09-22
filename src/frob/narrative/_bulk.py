"""`frob narrative move`'s bulk mode (T-4697): sweep a FILE or a
DIRECTORY (recursive) instead of hand-typing `file line` once per block.

T-4691 measured 507 over-cap comment runs across `src/frob` alone --
507 hand-typed invocations, each needing the agent to first find the
block's start line, is why the migration clusters (T-4709 etc.) exist as
separate tickets rather than one pass. This module is the sweep those
clusters actually run.

CONDENSING IS THE AUTHOR'S JOB (this module's own scope cut): a block
that mixes load-bearing utility with change-narrative still needs a
human/agent judgement call about which lines are which (`_migrate.py`'s
own docstring: "T-2993/T-2994 are explicit that which lines are
archaeology versus load-bearing utility is a judgement call, not a
regex"). Bulk mode therefore moves each block VERBATIM (no `keep_lines`
split) -- the per-block `--keep-file` escape hatch in `_cli.py`'s
existing `file line` form is how a caller keeps a load-bearing sentence
in place; that form is untouched by this module and stays the precise
tool for that job.

REUSES, NEVER REIMPLEMENTS: block/paragraph discovery goes through
`frob.gates._narrative_blocks._iter_blocks` (the same `# T-####:`-lead
shape NARR001 already detects) for source files and a bespoke ticket-
citing-paragraph scan for markdown, and the actual move goes through
`frob.narrative._migrate.migrate_block` plus `frob.tickets.set_body`
(T-2678's archived-ticket-safe front door) -- the identical engine
`_cli.py`'s single-block path already uses, so this module owns only
discovery, dispatch, and reporting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from frob.gates._narrative_blocks import _iter_blocks
from frob.logging import get_logger
from frob.narrative._migrate import (
    MigrateError,
    migrate_block,
    moved_text_for_ticket,
    split_ticket_id,
)

_log = get_logger(__name__)

__all__ = [
    "BulkItem",
    "BulkPlan",
    "apply_bulk",
    "discover_targets",
    "find_blocks",
    "plan_bulk",
]

_TICKET_ID_RE = re.compile(r"T-\d{2,6}")
_SCANNED_SUFFIXES = (".py", ".strata", ".md")
# `_migrate.migrate_block`'s own one-line replacement text (both the
# "# see T-####" code-comment shape and the "See T-#### for the history
# behind this." markdown shape) still cites a ticket id, so a naive
# re-scan would rediscover it as a fresh block forever -- idempotency
# (T-2994 constraint 4) requires this be recognized and skipped, not
# just relying on the original block no longer existing.
_REFERENCE_LINE_RE = re.compile(
    r"^\s*#?\s*see\s+T-\d{2,6}\b.*history behind this", re.IGNORECASE
)


# frob:doc docs/commands/narrative.md#bulk-mode-t-4697
@dataclass(frozen=True)
class BulkItem:
    """One block bulk mode found: its location, the ticket id it cites
    (`None` when it cites none), and -- once dispatched -- what happened
    to it. `status` is `"planned"` (dry-run), `"moved"`, `"skipped"`, or
    `"no-op"` (already migrated, T-2994 constraint 4)."""

    rel_path: str
    start_line: int
    end_line: int
    ticket_id: str | None
    status: str
    detail: str


# frob:doc docs/commands/narrative.md#bulk-mode-t-4697
@dataclass(frozen=True)
class BulkPlan:
    """`plan_bulk`'s result: every `BulkItem` found under the swept path,
    whether or not `--apply` follows. Printing this IS `--apply`'s
    absence -- `apply_bulk` with `apply=False` returns the identical
    plan, writing nothing (T-4697's own "omit --apply -> print only"
    acceptance criterion)."""

    items: tuple[BulkItem, ...]

    # frob:doc docs/commands/narrative.md#bulk-mode-t-4697
    @property
    def moved_count(self) -> int:
        """How many items this plan's `apply_bulk` run actually moved."""
        return sum(1 for i in self.items if i.status == "moved")

    # frob:doc docs/commands/narrative.md#bulk-mode-t-4697
    @property
    def skipped_count(self) -> int:
        """How many items this plan's `apply_bulk` run skipped (no
        ticket cited, or the cited ticket does not exist)."""
        return sum(1 for i in self.items if i.status == "skipped")


def _find_markdown_paragraphs(text: str) -> list[tuple[int, int]]:
    """Blank-line-delimited paragraph ranges (1-indexed, inclusive) that
    cite a `T-####` id anywhere in their text -- the markdown counterpart
    to `_iter_blocks`'s `# T-####:`-lead comment scan, matching
    `_migrate.py`'s own `paragraph_at` extent shape (T-2995) but scanning
    a whole file instead of one caller-given start line."""
    lines = text.splitlines()
    n = len(lines)
    out: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if not lines[i].strip():
            i += 1
            continue
        start = i
        j = i + 1
        while j < n and lines[j].strip():
            j += 1
        para = lines[start:j]
        is_reference_only = len(para) == 1 and _REFERENCE_LINE_RE.match(para[0])
        if not is_reference_only and any(_TICKET_ID_RE.search(ln) for ln in para):
            out.append((start + 1, j))
        i = j
    return out


# frob:doc docs/commands/narrative.md#bulk-mode-t-4697
def find_blocks(path: Path, text: str) -> tuple[tuple[int, int], ...]:
    """Every candidate block/paragraph in `text` bulk mode should attempt
    to migrate: `.py`/`.strata` via `_iter_blocks` (NARR001's own
    `# T-####:`-lead comment-run scan, reused rather than reimplemented),
    `.md` via `_find_markdown_paragraphs`. Any other suffix yields no
    blocks -- bulk mode is a no-op on a file type narrative migration
    does not apply to."""
    if path.suffix == ".md":
        return tuple(_find_markdown_paragraphs(text))
    if path.suffix in (".py", ".strata"):
        lines = text.splitlines()
        return tuple((s + 1, e + 1) for s, e in _iter_blocks(lines))
    return ()


# frob:doc docs/commands/narrative.md#bulk-mode-t-4697
def discover_targets(target: Path) -> tuple[Path, ...]:
    """The file(s) bulk mode sweeps: `target` itself if it is a file, or
    every `.py`/`.strata`/`.md` file under it (recursive, sorted for a
    deterministic plan) if it is a directory."""
    if target.is_file():
        return (target,)
    return tuple(
        sorted(
            p
            for p in target.rglob("*")
            if p.is_file() and p.suffix in _SCANNED_SUFFIXES
        )
    )


def _ticket_id_for_block(path: Path, text: str, start: int, end: int) -> str | None:
    """The `T-####` id a block/paragraph cites, or `None` -- tries the
    lead line first (the common case, matching `_migrate.py`'s own
    `split_ticket_id` shape) then falls back to a whole-block search so a
    markdown paragraph or a non-lead citation still resolves."""
    lines = text.splitlines()
    block = lines[start - 1 : end]
    if not block:
        return None
    return split_ticket_id(block[0]) or split_ticket_id("\n".join(block))


# frob:doc docs/commands/narrative.md#bulk-mode-t-4697
def plan_bulk(target: Path) -> BulkPlan:
    """The dry-run plan: every block bulk mode would attempt across
    `discover_targets(target)`, each item's `status` fixed at
    `"planned"` and `ticket_id` already resolved -- this is exactly what
    prints when `--apply` is omitted, and exactly what `apply_bulk`
    iterates to do the real work."""
    items: list[BulkItem] = []
    for path in discover_targets(target):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("narrative bulk: could not read %s: %s", path, exc)
            continue
        rel = str(path)
        for start, end in find_blocks(path, text):
            ticket_id = _ticket_id_for_block(path, text, start, end)
            items.append(
                BulkItem(
                    rel_path=rel,
                    start_line=start,
                    end_line=end,
                    ticket_id=ticket_id,
                    status="planned",
                    detail="no ticket cited -- would be skipped"
                    if ticket_id is None
                    else f"would move into {ticket_id}",
                )
            )
    return BulkPlan(items=tuple(items))


def _apply_one(
    *,
    path: Path,
    text: str,
    start: int,
    end: int,
    ticket_id: str | None,
    reason: str,
    root: Path,
) -> tuple[str, str, str]:  # noqa: ANN001
    """Dispatch one block: returns `(new_status, detail, new_text)` --
    `new_text` is `text` unchanged unless this item actually moved.
    Split out of `apply_bulk` to keep that function under ARCH001's
    threshold."""
    from frob.tickets import set_body

    if ticket_id is None:
        return "skipped", "no ticket cited -- never invented, never deleted", text

    lines = text.splitlines()
    moved_lines = tuple(lines[start - 1 : end])
    result = migrate_block(
        rel_path=str(path),
        file_text=text,
        start_line=start,
        end_line=end,
        existing_ticket_body="",
    )
    if result.is_err:
        err = result.danger_err
        if err is MigrateError.AlreadyMigrated:
            return "no-op", "already migrated", text
        return "skipped", f"refused: {err}", text

    migration = result.danger_ok
    ticket_body_text = moved_text_for_ticket(
        rel_path=str(path),
        start_line=start,
        moved_lines=moved_lines,
        ticket_id=ticket_id,
    )
    marker_line = ticket_body_text.splitlines()[0]

    from frob.tickets import load_queue

    queue = load_queue(root)
    if queue.is_ok and ticket_id in queue.danger_ok.tickets:
        if marker_line in queue.danger_ok.tickets[ticket_id].body:
            return "no-op", "already migrated", text

    from frob.tickets._models import TicketError

    write_result = set_body(
        root, ticket_id, ticket_body_text, mode="append", reason=reason
    )
    if write_result.is_err:
        if write_result.danger_err is TicketError.NotFound:
            return "skipped", f"{ticket_id} does not exist -- never invented", text
        return "skipped", f"ticket body append failed: {write_result.danger_err}", text

    return "moved", f"moved into {ticket_id}", migration.new_file_text


# frob:doc docs/commands/narrative.md#bulk-mode-t-4697
def apply_bulk(target: Path, *, apply: bool, reason: str, root: Path) -> BulkPlan:
    """Sweep `target` (file or directory): with `apply=False` (the
    default a bare `frob narrative move <path>` gets), returns
    `plan_bulk(target)` untouched -- neither a file nor a ticket is
    written. With `apply=True`, moves every block that cites a ticket
    that actually exists (live or archived -- `set_body` is the same
    archived-safe front door `_cli.py`'s single-block path already uses,
    T-2994 constraint 3), leaves a one-line `# see T-####` reference in
    place of it, skips (never deletes, never invents a ticket) a block
    that cites no ticket or a ticket that does not exist, and is
    idempotent (T-2994 constraint 4): a second `--apply` over the same
    tree changes nothing, because `migrate_block`'s own marker check
    (and this function's own pre-write queue check) recognizes an
    already-moved block and reports it `"no-op"` rather than re-moving
    or re-appending it."""
    if not apply:
        return plan_bulk(target)

    items: list[BulkItem] = []
    for path in discover_targets(target):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            _log.warning("narrative bulk: could not read %s: %s", path, exc)
            continue
        blocks = find_blocks(path, text)
        # Walk back-to-front so an earlier move's line-count shrink never
        # invalidates a later block's already-resolved (start, end) pair;
        # collect this file's items separately so they can be restored to
        # forward (document) order before joining the overall report.
        file_items: list[BulkItem] = []
        moved_any = False
        for start, end in reversed(blocks):
            ticket_id = _ticket_id_for_block(path, text, start, end)
            status, detail, text = _apply_one(
                path=path,
                text=text,
                start=start,
                end=end,
                ticket_id=ticket_id,
                reason=reason,
                root=root,
            )
            moved_any = moved_any or status == "moved"
            file_items.append(
                BulkItem(
                    rel_path=str(path),
                    start_line=start,
                    end_line=end,
                    ticket_id=ticket_id,
                    status=status,
                    detail=detail,
                )
            )
        if moved_any:
            path.write_text(text, encoding="utf-8")
        items.extend(reversed(file_items))
    return BulkPlan(items=tuple(items))

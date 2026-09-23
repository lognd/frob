"""frob.tickets._reporting_attachments -- the attach()/attachment-write family
(T-1420 LARGE001 split of `_reporting.py`): copying a file or clipboard image
into a ticket's attachment directory and recording it on the ticket
(`attach`, `_attachment_bytes`, `_next_attachment_path`, `_record_attachment`).

Split verbatim out of `frob.tickets._reporting` -- same T-1103/T-1171
per-family extraction pattern (directives intact, public surface
re-exported, zero caller-visible behavior change). Kept as its own module
rather than folded elsewhere because this quartet is the one concern in the
former `_reporting.py` that touches the filesystem (writing bytes, hashing,
building attachment paths) rather than mutating ticket body/metadata prose
in place -- a distinct I/O boundary from the done-report/review/drop family
that stays behind in `_reporting.py`.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import Attachment, AttachmentSource, Ticket, TicketError
from frob.tickets._store import (
    _store_mode,
    atomic_write,
    attachments_dir,
    read_done_report,
    slugify,
    tickets_dir,
    v2_attachments_dir,
    write_ticket,
)
from frob.tickets._worktree_guard import enforce_worktree_lease
from frob.tickets.clipboard import ClipboardError, clipboard_image

_log = get_logger(__name__)


# frob:ticket T-5151
# frob:doc docs/modules/tickets.md#public-api
# tests/test_tickets.py::TestRemoveAttachment.test_refuses_when_cited_in_done_report
class AttachRemoveError(ErrorSet):
    """Fallible outcomes specific to `remove_attachment` (T-5151) -- kept
    as its own `ErrorSet`, sibling to `TicketError`/`ClipboardError`
    (`clipboard.py`'s own precedent) rather than a new `TicketError`
    member, because `src/frob/tickets/_models.py` is outside this
    ticket's declared scope (leased by T-5133 for the whole worktree's
    lifetime) and every other error family in this package already lives
    beside the module that raises it."""

    NoMatchingAttachment = "no attachment on this ticket matches the given path"
    AttachmentInDoneReport = (
        "attachment path is quoted in the ticket's done-report -- removing it "
        "would silently invalidate cited evidence; use a different path or "
        "amend the done-report first"
    )


AttachError = TicketError | ClipboardError | AttachRemoveError

_MAX_WARN_BYTES = 1024 * 1024


def _attachment_bytes(
    ticket_id: str, source: AttachmentSource
) -> Result[tuple[bytes, str], AttachError]:
    """Read attachment `(data, suffix)` from the clipboard or `source.path`."""
    if source.path is None:
        _log.debug("tickets: attach %s from clipboard", ticket_id)
        image_result = clipboard_image()
        if image_result.is_err:
            return Err(image_result.danger_err)
        return Ok((image_result.danger_ok, ".png"))
    _log.debug("tickets: attach %s from %s", ticket_id, source.path)
    try:
        data = source.path.read_bytes()
    except OSError as exc:
        _log.error("tickets: failed to read attachment source %s: %s", source.path, exc)
        return Err(TicketError.WriteFailed)
    return Ok((data, source.path.suffix or ".png"))


# frob:doc docs/modules/tickets.md#public-api
def attach(
    root: Path, ticket_id: str, source: AttachmentSource, caption: str
) -> Result[Attachment, AttachError]:
    """Copy a file (or clipboard image) into tickets/attachments/<id>/ and record it."""
    from frob.tickets import _load_one

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    bytes_result = _attachment_bytes(ticket_id, source)
    if bytes_result.is_err:
        return Err(bytes_result.danger_err)
    data, suffix = bytes_result.danger_ok

    if len(data) > _MAX_WARN_BYTES:
        _log.warning(
            "tickets: attachment for %s is %d bytes (>1MB)", ticket_id, len(data)
        )

    sha256 = hashlib.sha256(data).hexdigest()
    dest_path = _next_attachment_path(root, ticket_id, caption, suffix)

    write_result = atomic_write(dest_path, data)
    if write_result.is_err:
        return Err(write_result.danger_err)

    return _record_attachment(root, ticket, dest_path, caption, sha256)


def _next_attachment_path(
    root: Path, ticket_id: str, caption: str, suffix: str
) -> Path:
    """The next `NN-slug.ext` attachment path under the ticket's attachment
    dir -- `tickets/T-####/attachments/` in v2 mode (design section 8's
    self-contained layout), else the legacy shared `tickets/attachments/
    <id>/` side-channel."""
    dest_dir = (
        v2_attachments_dir(root, ticket_id)
        if _store_mode(root) == "v2"
        else attachments_dir(root, ticket_id)
    )
    existing = sorted(dest_dir.glob("[0-9][0-9]-*")) if dest_dir.exists() else []
    next_index = len(existing) + 1
    return dest_dir / f"{next_index:02d}-{slugify(caption)}{suffix}"


def _record_attachment(
    root: Path, ticket: Ticket, dest_path: Path, caption: str, sha256: str
) -> Result[Attachment, AttachError]:
    """Append the written attachment to `ticket` and persist the ticket.

    `Attachment.path` is always stored relative to `tickets_dir(root)`, in
    BOTH modes -- `frob.gates`' COV004 sha-verification reconstructs the
    absolute path as `Path("tickets") / attachment.path`
    (`src/frob/gates/__init__.py`), a convention this module must not
    silently break for v2 tickets. v2's own attachment dir
    (`tickets/T-####/attachments/`) already nests under `tickets_dir`, so
    the stored value naturally comes out as `T-####/attachments/NN-x.ext`
    with no v2-specific branch needed here."""
    rel_path = dest_path.relative_to(tickets_dir(root)).as_posix()
    attachment = Attachment(path=rel_path, caption=caption, sha256=sha256)
    updated = ticket.model_copy(
        update={"attachments": ticket.attachments + (attachment,)}
    )
    frontmatter_write = write_ticket(root, updated)
    if frontmatter_write.is_err:
        return Err(frontmatter_write.danger_err)
    _log.info(
        "tickets: attached %s to %s (sha256=%s)", dest_path.name, ticket.id, sha256
    )
    return Ok(attachment)


def _resolve_remove_targets(
    ticket: Ticket, ticket_id: str, path: str | None, *, remove_all: bool
) -> Result[list[Attachment], AttachRemoveError]:
    """Pick which `Attachment` record(s) `remove_attachment` should act on:
    every attachment when `remove_all`, else every attachment whose
    `.path` matches `path` exactly or by basename (T-5151)."""
    if remove_all:
        return Ok(list(ticket.attachments))
    if not path:
        _log.error("tickets: remove_attachment %s: no path given", ticket_id)
        return Err(AttachRemoveError.NoMatchingAttachment)
    targets = [
        a for a in ticket.attachments if a.path == path or Path(a.path).name == path
    ]
    if not targets:
        _log.error(
            "tickets: remove_attachment %s: no attachment matches %r",
            ticket_id,
            path,
        )
        return Err(AttachRemoveError.NoMatchingAttachment)
    return Ok(targets)


def _refuse_if_cited_in_done_report(
    root: Path, ticket: Ticket, ticket_id: str, targets: list[Attachment]
) -> Result[None, AttachRemoveError]:
    """Refuse `remove_attachment` when any of `targets` is quoted in the
    ticket's done-report text (T-5151). `read_done_report` is v2-mode
    only (the split `done-report.md` file); legacy-mode tickets still
    carry their done-report prose inside `ticket.body` under a `## Done
    report` heading, so both are checked -- the refusal must not silently
    stop firing just because a ticket predates the v2 store split."""
    report_text = (read_done_report(root, ticket_id) or "") + ticket.body
    if not report_text:
        return Ok(None)
    cited = [a for a in targets if a.path in report_text]
    if not cited:
        return Ok(None)
    _log.error(
        "tickets: remove_attachment %s: refusing -- cited in done-report: %s",
        ticket_id,
        [a.path for a in cited],
    )
    return Err(AttachRemoveError.AttachmentInDoneReport)


def _delete_attachment_files(
    root: Path, targets: list[Attachment]
) -> Result[None, TicketError]:
    """Unlink every attachment file in `targets` from disk (T-5151);
    missing files are tolerated (`missing_ok=True`) since a prior
    partial failure or manual cleanup must not block the ledger-record
    removal that follows."""
    for attachment in targets:
        abs_path = tickets_dir(root) / attachment.path
        try:
            abs_path.unlink(missing_ok=True)
        except OSError as exc:
            _log.error("tickets: failed to delete attachment %s: %s", abs_path, exc)
            return Err(TicketError.WriteFailed)
    return Ok(None)


# frob:ticket T-5151
# frob:doc docs/modules/tickets.md#public-api
# tests/test_tickets.py::TestRemoveAttachment.test_removes_file_and_ledger_record
def remove_attachment(
    root: Path, ticket_id: str, path: str | None, *, remove_all: bool = False
) -> Result[tuple[Attachment, ...], AttachError]:
    """`frob ticket attach <id> --remove PATH` / `--remove-all` (T-5151):
    delete the attachment file(s) from disk, drop the matching
    `Attachment` record(s) from the ticket, and persist -- the removal
    counterpart to `attach()`'s write path, same worktree-lease and
    ledger-write discipline (single-ticket-id auto-commit dispatch, T-1615,
    handles the commit generically same as `attach` itself never commits
    by hand).

    `path` matches an `Attachment.path` either exactly (the stored
    `T-####/attachments/NN-x.ext`-shaped value) or by basename, so a
    caller can pass either the ledger-relative path or just the file's own
    name. Refuses with `AttachRemoveError.AttachmentInDoneReport` when a
    targeted attachment's path is quoted inside the ticket's done-report
    text -- deleting evidence a closed ticket's report already cites would
    silently invalidate that report (measured 2026-09-20 request)."""
    from frob.tickets import _load_one

    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    targets_result = _resolve_remove_targets(
        ticket, ticket_id, path, remove_all=remove_all
    )
    if targets_result.is_err:
        return Err(targets_result.danger_err)
    targets = targets_result.danger_ok
    if not targets:
        _log.info("tickets: remove_attachment %s: nothing to remove", ticket_id)
        return Ok(())

    cited_check = _refuse_if_cited_in_done_report(root, ticket, ticket_id, targets)
    if cited_check.is_err:
        return Err(cited_check.danger_err)

    deleted = _delete_attachment_files(root, targets)
    if deleted.is_err:
        return Err(deleted.danger_err)

    remaining = tuple(a for a in ticket.attachments if a not in targets)
    updated = ticket.model_copy(update={"attachments": remaining})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)

    _log.info(
        "tickets: removed %d attachment(s) from %s: %s",
        len(targets),
        ticket_id,
        [a.path for a in targets],
    )
    return Ok(tuple(targets))

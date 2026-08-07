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

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import Attachment, AttachmentSource, Ticket, TicketError
from frob.tickets._store import (
    _store_mode,
    atomic_write,
    attachments_dir,
    slugify,
    tickets_dir,
    v2_attachments_dir,
    write_ticket,
)
from frob.tickets._worktree_guard import enforce_worktree_lease
from frob.tickets.clipboard import ClipboardError, clipboard_image

_log = get_logger(__name__)

AttachError = TicketError | ClipboardError

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
    rel_path = str(dest_path.relative_to(tickets_dir(root)))
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

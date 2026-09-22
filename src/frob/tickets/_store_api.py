# frob:ticket T-4657
"""Typed ledger store API: the one seam every frob module reads and writes
tickets through.

Kernel decoupling (T-4651/T-4652): today ticket data is reached a dozen
different ways across ``src/frob/tickets/*.py`` and
``src/frob/app/ticket_runner/*.py`` -- there is no single seam, which is why
the ledger, the leases and the land pipeline cannot be decoupled from each
other. This module is that seam: pydantic models in, pydantic models out,
every fallible operation returns a typani ``Result`` rather than raising.
Nothing outside ``_store.py`` (the mode-dispatched on-disk implementation
this module wraps) and this module should open a ``tickets/<id>/ticket.md``
path directly; new callers go through the functions below instead.

This leaf introduces the seam and does not change the on-disk ticket.md
format, the CLI surface or the comment DSL -- it wraps the existing
``_store.py`` implementation rather than replacing it. Migrating the
remaining direct readers/writers onto this seam is deliberately left to
follow-up tickets (see docs/modules/tickets-data-storage.md).
"""

from __future__ import annotations

from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import Ticket, TicketError
from frob.tickets._store import (
    load_all,
    load_archive,
    write_archived_ticket,
    write_ticket,
)

_log = get_logger(__name__)


# frob:doc docs/modules/tickets-data-storage.md#store-api-seam-t-4657
def get_ticket(root: Path, ticket_id: str) -> Result[Ticket, TicketError]:
    """Read one live ticket by id through the ledger store, or Err(NotFound).

    Logs the read at DEBUG on success and the refusal at WARNING when the
    id is absent or the underlying load fails.
    """
    loaded = load_all(root)
    if loaded.is_err:
        _log.warning(
            "tickets: store_api get_ticket(%s) refused -- ledger load failed: %s",
            ticket_id,
            loaded.danger_err,
        )
        return Err(loaded.danger_err)
    tickets = loaded.danger_ok
    ticket = tickets.get(ticket_id)
    if ticket is None:
        _log.warning(
            "tickets: store_api get_ticket(%s) refused -- not found", ticket_id
        )
        return Err(TicketError.NotFound)
    _log.debug("tickets: store_api get_ticket(%s) ok", ticket_id)
    return Ok(ticket)


# frob:doc docs/modules/tickets-data-storage.md#store-api-seam-t-4657
def list_tickets(root: Path) -> Result[dict[str, Ticket], TicketError]:
    """Every live ticket in the repo as an id -> Ticket map, mode-agnostic.

    Thin, logged wrapper around ``_store.load_all``; the mapping's values
    are ``Ticket`` pydantic models, never raw dicts.
    """
    loaded = load_all(root)
    if loaded.is_err:
        _log.warning(
            "tickets: store_api list_tickets() refused -- ledger load failed: %s",
            loaded.danger_err,
        )
        return Err(loaded.danger_err)
    _log.debug(
        "tickets: store_api list_tickets() ok (%d ticket(s))", len(loaded.danger_ok)
    )
    return Ok(loaded.danger_ok)


# frob:doc docs/modules/tickets-data-storage.md#store-api-seam-t-4657
def put_ticket(
    root: Path, ticket: Ticket, *, strict_no_content_loss: bool = True
) -> Result[None, TicketError]:
    """Upsert one live ticket through the ledger store (atomic, logged).

    Thin wrapper around ``_store.write_ticket``; ``strict_no_content_loss``
    is forwarded unchanged so callers keep the existing T-1679 guard
    against a write silently discarding evidence or a Done report.
    """
    written = write_ticket(root, ticket, strict_no_content_loss=strict_no_content_loss)
    if written.is_err:
        _log.warning(
            "tickets: store_api put_ticket(%s) refused: %s",
            ticket.id,
            written.danger_err,
        )
        return Err(written.danger_err)
    _log.debug("tickets: store_api put_ticket(%s) ok", ticket.id)
    return Ok(None)


# frob:doc docs/modules/tickets-data-storage.md#store-api-seam-t-4657
def get_archived_ticket(root: Path, ticket_id: str) -> Result[Ticket, TicketError]:
    """Read one archived ticket by id through the ledger store.

    Mirrors ``get_ticket`` but reads the archive backend; Err(NotFound)
    when the id is not in the archive.
    """
    loaded = load_archive(root)
    if loaded.is_err:
        _log.warning(
            "tickets: store_api get_archived_ticket(%s) refused -- archive load "
            "failed: %s",
            ticket_id,
            loaded.danger_err,
        )
        return Err(loaded.danger_err)
    tickets = loaded.danger_ok
    ticket = tickets.get(ticket_id)
    if ticket is None:
        _log.warning(
            "tickets: store_api get_archived_ticket(%s) refused -- not found",
            ticket_id,
        )
        return Err(TicketError.NotFound)
    _log.debug("tickets: store_api get_archived_ticket(%s) ok", ticket_id)
    return Ok(ticket)


# frob:doc docs/modules/tickets-data-storage.md#store-api-seam-t-4657
def list_archived_tickets(root: Path) -> Result[dict[str, Ticket], TicketError]:
    """Every archived ticket in the repo as an id -> Ticket map.

    Thin, logged wrapper around ``_store.load_archive``.
    """
    loaded = load_archive(root)
    if loaded.is_err:
        _log.warning(
            "tickets: store_api list_archived_tickets() refused -- archive load "
            "failed: %s",
            loaded.danger_err,
        )
        return Err(loaded.danger_err)
    _log.debug(
        "tickets: store_api list_archived_tickets() ok (%d ticket(s))",
        len(loaded.danger_ok),
    )
    return Ok(loaded.danger_ok)


# frob:doc docs/modules/tickets-data-storage.md#store-api-seam-t-4657
def put_archived_ticket(root: Path, ticket: Ticket) -> Result[None, TicketError]:
    """Upsert one archived ticket through the ledger store (atomic, logged).

    Thin wrapper around ``_store.write_archived_ticket``.
    """
    written = write_archived_ticket(root, ticket)
    if written.is_err:
        _log.warning(
            "tickets: store_api put_archived_ticket(%s) refused: %s",
            ticket.id,
            written.danger_err,
        )
        return Err(written.danger_err)
    _log.debug("tickets: store_api put_archived_ticket(%s) ok", ticket.id)
    return Ok(None)

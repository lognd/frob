"""
frob.tickets -- statically-checkable ticket and feature queue (docs/tickets.md).

A git-tracked queue of tickets (features, bugs, audits, invariant work) with
a state machine, blockers, evidence, failure memory, and image attachments --
the shared work surface for the human and every agent. No dependency on
frob.graph or frob.lang by design (see docs/rework.md cycle-avoidance).
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import (
    Attachment,
    AttachmentSource,
    FailureEntry,
    Origin,
    Stride,
    Ticket,
    TicketError,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
)
from frob.tickets._store import (
    atomic_write,
    attachments_dir,
    load_all,
    migrate_to_ledger,
    slugify,
    tickets_dir,
    write_all,
    write_ticket,
)
from frob.tickets.clipboard import ClipboardError, clipboard_image

_log = get_logger(__name__)

AttachError = TicketError | ClipboardError

_MAX_WARN_BYTES = 1024 * 1024

# state machine: legal `from` -> {legal `to` states}
_TRANSITIONS: dict[TicketState, frozenset[TicketState]] = {
    TicketState.QUEUED: frozenset({TicketState.PLANNED, TicketState.DROPPED}),
    TicketState.PLANNED: frozenset({TicketState.IN_PROGRESS, TicketState.DROPPED}),
    TicketState.IN_PROGRESS: frozenset(
        {
            TicketState.DONE,
            TicketState.BLOCKED,
            TicketState.QUEUED,
            TicketState.DROPPED,
        }
    ),
    TicketState.BLOCKED: frozenset({TicketState.IN_PROGRESS, TicketState.DROPPED}),
    TicketState.DONE: frozenset(),
    TicketState.DROPPED: frozenset(),
}

_OPEN_STATES = frozenset(
    s for s in TicketState if s not in (TicketState.DONE, TicketState.DROPPED)
)

_DONE_REPORT_HEADING = "## Done report"
_FAILURE_LOG_HEADING = "## Failure log"


# frob:invariant INV-004
# frob:doc docs/tickets.md#public-api
def load_queue(root: Path) -> Result[TicketQueue, TicketError]:
    """Load every ticket (single-file ledger or legacy dir); malformation is Err."""
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    tickets = loaded.danger_ok
    _log.debug("tickets: loaded %d ticket(s) under %s", len(tickets), root)
    return Ok(TicketQueue(tickets=tickets))


def migrate(root: Path) -> Result[int, TicketError]:
    """Collapse legacy tickets/*.md files into the single tickets.md ledger."""
    return migrate_to_ledger(root)


# frob:doc docs/tickets.md#public-api
def new_ticket(root: Path, spec: TicketSpec) -> Result[Ticket, TicketError]:
    """Allocate the next sequential id and upsert the ticket into the store."""
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    existing = loaded.danger_ok
    max_num = 0
    for tid in existing:
        try:
            max_num = max(max_num, int(tid.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    ticket_id = f"T-{max_num + 1:04d}"
    if ticket_id in existing:
        _log.error("tickets: id collision allocating %s", ticket_id)
        return Err(TicketError.DuplicateId)
    body = spec.body
    if spec.kind == TicketKind.INCIDENT and not body.strip():
        body = _INCIDENT_TEMPLATE
    ticket = Ticket(
        id=ticket_id,
        title=spec.title,
        state=TicketState.QUEUED,
        kind=spec.kind,
        origin=spec.origin,
        created=date.today(),
        blocked_by=spec.blocked_by,
        parent=spec.parent,
        scope=spec.scope,
        evidence=(),
        attachments=(),
        acceptance=spec.acceptance,
        threat=spec.threat,
        body=body,
    )
    write_result = write_ticket(root, ticket)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info("tickets: created %s", ticket_id)
    return Ok(ticket)


_INCIDENT_TEMPLATE = (
    "## Summary\n\n"
    "## Timeline\n\n"
    "## Root cause (blameless)\n\n"
    "## Action items\n"
    "<!-- each action item MUST become a ticket -- link them here as T-#### -->\n"
)


def renumber(root: Path) -> Result[int, TicketError]:
    """Reassign ticket ids to a contiguous T-0001.. sequence (ordered by
    current id), rewriting blocked_by/parent references so the queue stays
    consistent. The remedy for sequential-id collisions after a worktree
    merge (T-0012). Returns the number of tickets renumbered.
    """
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    old = loaded.danger_ok
    ordered = sorted(old.values(), key=lambda t: t.id)
    mapping = {t.id: f"T-{i + 1:04d}" for i, t in enumerate(ordered)}
    if all(t.id == mapping[t.id] for t in ordered):
        _log.info("tickets: renumber -- already contiguous, nothing to do")
        return Ok(0)

    def remap(tid: str) -> str:
        return mapping.get(tid, tid)

    new_map: dict[str, Ticket] = {}
    renumbered = 0
    for ticket in ordered:
        new_id = mapping[ticket.id]
        if new_id != ticket.id:
            renumbered += 1
        new_map[new_id] = ticket.model_copy(
            update={
                "id": new_id,
                "blocked_by": tuple(remap(b) for b in ticket.blocked_by),
                "parent": remap(ticket.parent) if ticket.parent else None,
            }
        )
    result = write_all(root, new_map)
    if result.is_err:
        return Err(result.danger_err)
    _log.info("tickets: renumbered %d ticket(s)", renumbered)
    return Ok(renumbered)


# frob:doc docs/tickets.md#public-api
def doable(queue: TicketQueue) -> tuple[Ticket, ...]:
    """Tickets in {queued, planned} with no open blockers, ordered oldest-first."""
    candidates = [
        t
        for t in queue.tickets.values()
        if t.state in (TicketState.QUEUED, TicketState.PLANNED)
        and not _open_blockers(queue, t)
    ]
    candidates.sort(key=lambda t: (t.created, t.id))
    return tuple(candidates)


def _open_blockers(queue: TicketQueue, ticket: Ticket) -> tuple[str, ...]:
    """Blocker ids of ticket whose current state is not done/dropped (or unknown)."""
    open_ids: list[str] = []
    for blocker_id in ticket.blocked_by:
        blocker = queue.tickets.get(blocker_id)
        if blocker is None or blocker.state in _OPEN_STATES:
            open_ids.append(blocker_id)
    return tuple(open_ids)


def _load_one(root: Path, ticket_id: str) -> Result[Ticket, TicketError]:
    """Load a single ticket by id from whichever backend the repo uses."""
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok.get(ticket_id)
    if ticket is None:
        _log.warning("tickets: %s not found under %s", ticket_id, root)
        return Err(TicketError.NotFound)
    return Ok(ticket)


def _has_done_report(body: str) -> bool:
    """Whether body contains a '## Done report' section heading."""
    return any(line.strip() == _DONE_REPORT_HEADING for line in body.splitlines())


# frob:invariant INV-002
# frob:doc docs/tickets.md#public-api
def transition(
    root: Path, ticket_id: str, to: TicketState
) -> Result[Ticket, TicketError]:
    """Enforce the state machine; `done` also requires evidence and a Done report."""
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    queue = loaded.danger_ok
    ticket = queue.get(ticket_id)
    if ticket is None:
        _log.warning("tickets: %s not found under %s", ticket_id, root)
        return Err(TicketError.NotFound)

    allowed = _TRANSITIONS.get(ticket.state, frozenset())
    if to not in allowed:
        _log.warning(
            "tickets: %s illegal transition %s -> %s", ticket_id, ticket.state, to
        )
        return Err(TicketError.InvalidTransition)

    if to == TicketState.IN_PROGRESS:
        open_ids = [
            b
            for b in ticket.blocked_by
            if b not in queue or queue[b].state in _OPEN_STATES
        ]
        if open_ids:
            _log.warning(
                "tickets: %s cannot start, open blockers %s", ticket_id, open_ids
            )
            return Err(TicketError.BlockerOpen)

    if to == TicketState.DONE:
        if not ticket.evidence or not _has_done_report(ticket.body):
            _log.warning(
                "tickets: %s cannot close, missing evidence or Done report", ticket_id
            )
            return Err(TicketError.MissingEvidence)

    updated = ticket.model_copy(update={"state": to})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info("tickets: %s transitioned %s -> %s", ticket_id, ticket.state, to)
    return Ok(updated)


# frob:doc docs/tickets.md#public-api
def record_failure(
    root: Path, ticket_id: str, entry: FailureEntry
) -> Result[Ticket, TicketError]:
    """Append entry to the '## Failure log' body section, creating it if absent."""
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    line = f"- {entry.date.isoformat()} attempt {entry.attempt}: {entry.summary}"
    new_body = _append_to_section(ticket.body, _FAILURE_LOG_HEADING, line)
    updated = ticket.model_copy(update={"body": new_body})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info("tickets: %s recorded failure attempt %d", ticket_id, entry.attempt)
    return Ok(updated)


def _append_to_section(body: str, heading: str, line: str) -> str:
    """Append `line` under `heading` in body; create the section at the end if gone."""
    lines = body.splitlines()
    for i, text in enumerate(lines):
        if text.strip() != heading:
            continue
        insert_at = i + 1
        while insert_at < len(lines) and not lines[insert_at].startswith("## "):
            insert_at += 1
        while insert_at > i + 1 and lines[insert_at - 1].strip() == "":
            insert_at -= 1
        lines.insert(insert_at, line)
        return "\n".join(lines) + ("\n" if body.endswith("\n") else "")
    separator = (
        ""
        if not body or body.endswith("\n\n")
        else ("\n" if body.endswith("\n") else "\n\n")
    )
    return f"{body}{separator}{heading}\n{line}\n"


# frob:doc docs/tickets.md#public-api
def attach(
    root: Path, ticket_id: str, source: AttachmentSource, caption: str
) -> Result[Attachment, AttachError]:
    """Copy a file (or clipboard image) into tickets/attachments/<id>/ and record it."""
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    if source.path is None:
        _log.debug("tickets: attach %s from clipboard", ticket_id)
        image_result = clipboard_image()
        if image_result.is_err:
            return Err(image_result.danger_err)
        data = image_result.danger_ok
        suffix = ".png"
    else:
        _log.debug("tickets: attach %s from %s", ticket_id, source.path)
        try:
            data = source.path.read_bytes()
        except OSError as exc:
            _log.error(
                "tickets: failed to read attachment source %s: %s", source.path, exc
            )
            return Err(TicketError.WriteFailed)
        suffix = source.path.suffix or ".png"

    if len(data) > _MAX_WARN_BYTES:
        _log.warning(
            "tickets: attachment for %s is %d bytes (>1MB)", ticket_id, len(data)
        )

    sha256 = hashlib.sha256(data).hexdigest()
    dest_dir = attachments_dir(root, ticket_id)
    existing = sorted(dest_dir.glob("[0-9][0-9]-*")) if dest_dir.exists() else []
    next_index = len(existing) + 1
    slug = slugify(caption)
    dest_name = f"{next_index:02d}-{slug}{suffix}"
    dest_path = dest_dir / dest_name

    write_result = atomic_write(dest_path, data)
    if write_result.is_err:
        return Err(write_result.danger_err)

    rel_path = str(dest_path.relative_to(tickets_dir(root)))
    attachment = Attachment(path=rel_path, caption=caption, sha256=sha256)
    updated = ticket.model_copy(
        update={"attachments": ticket.attachments + (attachment,)}
    )
    frontmatter_write = write_ticket(root, updated)
    if frontmatter_write.is_err:
        return Err(frontmatter_write.danger_err)

    _log.info("tickets: attached %s to %s (sha256=%s)", dest_name, ticket_id, sha256)
    return Ok(attachment)


__all__ = [
    "Attachment",
    "AttachError",
    "AttachmentSource",
    "ClipboardError",
    "FailureEntry",
    "Origin",
    "Ticket",
    "TicketError",
    "TicketKind",
    "TicketQueue",
    "TicketSpec",
    "TicketState",
    "attach",
    "doable",
    "load_queue",
    "Stride",
    "migrate",
    "new_ticket",
    "renumber",
    "record_failure",
    "transition",
]

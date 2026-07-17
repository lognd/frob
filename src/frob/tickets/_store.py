"""Ticket file I/O: frontmatter/body split, (de)serialization, atomic writes.

The queue is a contract surface (see docs/tickets.md) -- every read is
strict (Err on any malformation) and every write is atomic (temp file +
os.replace in the same directory, so a crash mid-write never corrupts a
ticket file readers might concurrently observe).
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import yaml
from pydantic import ValidationError
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import Ticket, TicketError

_log = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n(.*)\Z", re.DOTALL)
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_TICKET_FILENAME_RE = re.compile(r"^T-(\d{4})-[a-z0-9-]+\.md$")


def slugify(title: str) -> str:
    """Lowercase, hyphenate, and strip non-alnum runs from a title for a filename."""
    slug = _SLUG_RE.sub("-", title.strip().lower()).strip("-")
    return slug or "untitled"


def tickets_dir(root: Path) -> Path:
    """The tickets/ directory under a project root."""
    return root / "tickets"


def attachments_dir(root: Path, ticket_id: str) -> Path:
    """The tickets/attachments/<id>/ directory for a given ticket."""
    return tickets_dir(root) / "attachments" / ticket_id


def ticket_glob(root: Path) -> list[Path]:
    """Every ticket markdown file directly under tickets/, unsorted."""
    d = tickets_dir(root)
    if not d.exists():
        return []
    return sorted(p for p in d.glob("T-*.md") if p.is_file())


def parse_ticket_file(path: Path) -> Result[Ticket, TicketError]:
    """Split a ticket file into frontmatter + body and validate it as a Ticket."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        _log.error("tickets: %s has no valid frontmatter block", path)
        return Err(TicketError.MalformedFrontmatter)
    raw_yaml, body = match.group(1), match.group(2)
    try:
        data = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        _log.error("tickets: %s frontmatter is not valid YAML: %s", path, exc)
        return Err(TicketError.MalformedFrontmatter)
    if not isinstance(data, dict):
        _log.error("tickets: %s frontmatter did not parse to a mapping", path)
        return Err(TicketError.MalformedFrontmatter)
    data["body"] = body
    try:
        ticket = Ticket.model_validate(data)
    except ValidationError as exc:
        _log.error("tickets: %s failed schema validation: %s", path, exc)
        return Err(TicketError.MalformedFrontmatter)
    _log.debug("tickets: parsed %s", path)
    return Ok(ticket)


def serialize_ticket(ticket: Ticket) -> str:
    """Render a Ticket back to frontmatter + body text (inverse of parse)."""
    payload = ticket.model_dump(mode="json", exclude={"body"})
    raw_yaml = yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)
    return f"---\n{raw_yaml}---\n{ticket.body}"


def ticket_path(root: Path, ticket_id: str, slug: str) -> Path:
    """The filename a given ticket id + slug maps to."""
    return tickets_dir(root) / f"{ticket_id}-{slug}.md"


def find_ticket_path(root: Path, ticket_id: str) -> Path | None:
    """Locate the on-disk file for a ticket id by scanning tickets/, None if absent."""
    for p in ticket_glob(root):
        m = _TICKET_FILENAME_RE.match(p.name)
        if m and f"T-{m.group(1)}" == ticket_id:
            return p
    return None


def atomic_write(path: Path, content: str | bytes) -> Result[None, TicketError]:
    """Write content via temp file + os.replace in the same directory (crash-safe)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = None if isinstance(content, bytes) else "utf-8"
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, mode, encoding=encoding) as f:
            f.write(content)
        os.replace(tmp_name, path)
    except OSError as exc:
        _log.error("tickets: atomic write to %s failed: %s", path, exc)
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        return Err(TicketError.WriteFailed)
    _log.info("tickets: wrote %s", path)
    return Ok(None)

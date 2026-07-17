"""Ticket storage: a single-file `tickets.md` ledger (default) or the legacy
one-file-per-ticket `tickets/*.md` layout, behind one interface.

The queue is a contract surface (docs/tickets.md): every read is strict
(Err on any malformation) and every write is atomic (temp file + os.replace
in the same directory, so a crash mid-write never corrupts what a
concurrent reader observes).

Two backends, auto-detected by `store_mode`:

- **single** (default for new repos): all tickets live in one `tickets.md`
  at the repo root, each a section delimited by a `<!-- ticket:T-#### -->`
  marker followed by a fenced ```yaml frontmatter block and a free markdown
  body. This is the compact central log -- one file, greppable, no sprawl.
- **dir** (legacy / back-compat): `tickets/T-####-slug.md`, one file each.

The public `Ticket` / `TicketQueue` shapes are identical across both, so
frob.gates and the CLI never see the difference.
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

# Single-file ledger: sections start at a `<!-- ticket:T-#### -->` marker.
_LEDGER_NAME = "tickets.md"
_LEDGER_MARKER_RE = re.compile(r"(?m)^<!-- ticket:(T-\d{4}) -->[ \t]*$")
_YAML_FENCE_RE = re.compile(r"\A\s*```ya?ml\n(.*?\n)```[ \t]*\n?(.*)\Z", re.DOTALL)
_LEDGER_HEADER = (
    "# Tickets\n\n"
    "Central ledger managed by `frob ticket` -- one section per ticket.\n"
)


def slugify(title: str) -> str:
    """Lowercase, hyphenate, and strip non-alnum runs from a title for a filename."""
    slug = _SLUG_RE.sub("-", title.strip().lower()).strip("-")
    return slug or "untitled"


def tickets_dir(root: Path) -> Path:
    """The legacy tickets/ directory (also holds attachments in single mode)."""
    return root / "tickets"


def ledger_path(root: Path) -> Path:
    """The single-file `tickets.md` ledger path at the repo root."""
    return root / _LEDGER_NAME


def attachments_dir(root: Path, ticket_id: str) -> Path:
    """The tickets/attachments/<id>/ directory for a given ticket (both modes)."""
    return tickets_dir(root) / "attachments" / ticket_id


def _dir_glob(root: Path) -> list[Path]:
    """Every legacy ticket markdown file directly under tickets/, sorted."""
    d = tickets_dir(root)
    if not d.exists():
        return []
    return sorted(p for p in d.glob("T-*.md") if p.is_file())


def store_mode(root: Path) -> str:
    """Which backend a repo uses: 'single' if tickets.md exists, 'dir' if only
    the legacy tickets/*.md files exist, else 'single' (the default for a
    fresh repo -- new ledgers are compact, not sprawling)."""
    if ledger_path(root).exists():
        return "single"
    if _dir_glob(root):
        return "dir"
    return "single"


# ---------------------------------------------------------------------------
# Serialization (shared)
# ---------------------------------------------------------------------------


def _frontmatter_yaml(ticket: Ticket) -> str:
    """The ticket's scalar/list fields as YAML (body excluded)."""
    payload = ticket.model_dump(mode="json", exclude={"body"})
    return yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)


def serialize_ticket(ticket: Ticket) -> str:
    """Render a Ticket to legacy `---`-frontmatter + body (dir-mode file text)."""
    return f"---\n{_frontmatter_yaml(ticket)}---\n{ticket.body}"


def _validate(data: dict, body: str, where: str) -> Result[Ticket, TicketError]:
    """Validate a frontmatter mapping + body into a Ticket, or a hard Err."""
    if not isinstance(data, dict):
        _log.error("tickets: %s frontmatter did not parse to a mapping", where)
        return Err(TicketError.MalformedFrontmatter)
    data = {**data, "body": body}
    try:
        return Ok(Ticket.model_validate(data))
    except ValidationError as exc:
        _log.error("tickets: %s failed schema validation: %s", where, exc)
        return Err(TicketError.MalformedFrontmatter)


# ---------------------------------------------------------------------------
# dir backend
# ---------------------------------------------------------------------------


def parse_ticket_file(path: Path) -> Result[Ticket, TicketError]:
    """Split a legacy ticket file into frontmatter + body and validate it."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        _log.error("tickets: %s has no valid frontmatter block", path)
        return Err(TicketError.MalformedFrontmatter)
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        _log.error("tickets: %s frontmatter is not valid YAML: %s", path, exc)
        return Err(TicketError.MalformedFrontmatter)
    return _validate(data, match.group(2), str(path))


def _dir_path_for(root: Path, ticket: Ticket) -> Path:
    """The tickets/T-####-slug.md path a ticket serializes to."""
    return tickets_dir(root) / f"{ticket.id}-{slugify(ticket.title)}.md"


def _find_dir_path(root: Path, ticket_id: str) -> Path | None:
    """Locate the legacy file for a ticket id by scanning tickets/."""
    for p in _dir_glob(root):
        m = _TICKET_FILENAME_RE.match(p.name)
        if m and f"T-{m.group(1)}" == ticket_id:
            return p
    return None


# ---------------------------------------------------------------------------
# single-file ledger backend
# ---------------------------------------------------------------------------


def _parse_ledger(text: str) -> Result[dict[str, Ticket], TicketError]:
    """Parse a `tickets.md` ledger into an id -> Ticket map (strict)."""
    tickets: dict[str, Ticket] = {}
    markers = list(_LEDGER_MARKER_RE.finditer(text))
    for i, marker in enumerate(markers):
        ticket_id = marker.group(1)
        chunk_end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        chunk = text[marker.end() : chunk_end]
        fence = _YAML_FENCE_RE.match(chunk.lstrip("\n"))
        if fence is None:
            _log.error("tickets: %s section has no ```yaml frontmatter", ticket_id)
            return Err(TicketError.MalformedFrontmatter)
        try:
            data = yaml.safe_load(fence.group(1))
        except yaml.YAMLError as exc:
            _log.error("tickets: %s frontmatter is not valid YAML: %s", ticket_id, exc)
            return Err(TicketError.MalformedFrontmatter)
        parsed = _validate(data, fence.group(2).strip("\n"), ticket_id)
        if parsed.is_err:
            return Err(parsed.danger_err)
        ticket = parsed.danger_ok
        if ticket.id != ticket_id:
            _log.error("tickets: marker %s wraps ticket %s", ticket_id, ticket.id)
            return Err(TicketError.MalformedFrontmatter)
        if ticket.id in tickets:
            _log.error("tickets: duplicate id %s in ledger", ticket.id)
            return Err(TicketError.DuplicateId)
        tickets[ticket.id] = ticket
    return Ok(tickets)


def _render_ledger(tickets: dict[str, Ticket]) -> str:
    """Render an id -> Ticket map to ledger text, ordered by id."""
    parts = [_LEDGER_HEADER]
    for ticket_id in sorted(tickets):
        ticket = tickets[ticket_id]
        body = ticket.body.strip("\n")
        section = (
            f"\n<!-- ticket:{ticket_id} -->\n"
            f"```yaml\n{_frontmatter_yaml(ticket)}```\n"
        )
        if body:
            section += f"{body}\n"
        parts.append(section)
    return "".join(parts)


# ---------------------------------------------------------------------------
# unified interface
# ---------------------------------------------------------------------------


def load_all(root: Path) -> Result[dict[str, Ticket], TicketError]:
    """Every ticket in the repo as an id -> Ticket map, backend-agnostic."""
    if store_mode(root) == "single":
        ledger = ledger_path(root)
        if not ledger.exists():
            return Ok({})
        return _parse_ledger(ledger.read_text(encoding="utf-8"))
    tickets: dict[str, Ticket] = {}
    for path in _dir_glob(root):
        parsed = parse_ticket_file(path)
        if parsed.is_err:
            _log.error("tickets: load aborted, %s is malformed", path)
            return Err(parsed.danger_err)
        ticket = parsed.danger_ok
        if ticket.id in tickets:
            _log.error("tickets: duplicate id %s (%s)", ticket.id, path)
            return Err(TicketError.DuplicateId)
        tickets[ticket.id] = ticket
    return Ok(tickets)


def write_ticket(root: Path, ticket: Ticket) -> Result[None, TicketError]:
    """Upsert one ticket into whichever backend the repo uses (atomic)."""
    if store_mode(root) == "single":
        existing = load_all(root)
        if existing.is_err:
            return Err(existing.danger_err)
        tickets = existing.danger_ok
        tickets[ticket.id] = ticket
        return atomic_write(ledger_path(root), _render_ledger(tickets))
    return atomic_write(_dir_path_for(root, ticket), serialize_ticket(ticket))


def migrate_to_ledger(root: Path) -> Result[int, TicketError]:
    """Collapse a legacy tickets/*.md layout into a single tickets.md ledger.

    Reads every dir-mode ticket, writes the ledger, then deletes the source
    files. Attachments under tickets/attachments/ are left untouched (both
    modes share that location). Returns the number of tickets migrated.
    """
    files = _dir_glob(root)
    if not files:
        return Ok(0)
    tickets: dict[str, Ticket] = {}
    for path in files:
        parsed = parse_ticket_file(path)
        if parsed.is_err:
            return Err(parsed.danger_err)
        tickets[parsed.danger_ok.id] = parsed.danger_ok
    written = atomic_write(ledger_path(root), _render_ledger(tickets))
    if written.is_err:
        return Err(written.danger_err)
    for path in files:
        try:
            path.unlink()
        except OSError as exc:
            _log.warning("tickets: could not remove migrated %s: %s", path, exc)
    _log.info("tickets: migrated %d ticket(s) into %s", len(tickets), ledger_path(root))
    return Ok(len(tickets))


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
    _log.debug("tickets: wrote %s", path)
    return Ok(None)

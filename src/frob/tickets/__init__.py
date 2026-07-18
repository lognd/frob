"""
frob.tickets -- statically-checkable ticket and feature queue (docs/modules/tickets.md).

A git-tracked queue of tickets (features, bugs, audits, invariant work) with
a state machine, blockers, evidence, failure memory, and image attachments --
the shared work surface for the human and every agent. No dependency on
frob.graph or frob.lang by design (see docs/rework.md cycle-avoidance).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._land import land, splice_ledger
from frob.tickets._models import (
    Attachment,
    AttachmentSource,
    FailureEntry,
    LandError,
    LandReport,
    Origin,
    RenumberReport,
    Stride,
    Ticket,
    TicketError,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
)
from frob.tickets._provisional import is_draft_id, mint_draft_id, on_default_branch
from frob.tickets._store import (
    archive_path,
    atomic_write,
    attachments_dir,
    ledger_path,
    load_all,
    load_archive,
    migrate_to_ledger,
    slugify,
    tickets_dir,
    write_all,
    write_archive,
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


# frob:doc docs/modules/tickets.md#public-api
# frob:waive TEST005 reason="load_active 80.0% branch cover, debt T-0160"
def load_active(root: Path) -> Result[TicketQueue, TicketError]:
    """Load only the active store (single-file ledger or legacy dir), NOT the
    archive -- the source `frob ticket list`/`doable` display against, so a
    growing pile of done tickets in tickets-archive.md never bloats them
    (T-0096)."""
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    tickets = loaded.danger_ok
    _log.debug("tickets: loaded %d active ticket(s) under %s", len(tickets), root)
    return Ok(TicketQueue(tickets=tickets))


def _load_merged(root: Path) -> Result[dict[str, Ticket], TicketError]:
    """Active-store tickets plus archived tickets, id-collision checked.

    The merge exists so id uniqueness and cross-references (blocked_by,
    parent, frob:ticket directives) keep resolving correctly after a ticket
    has been archived -- a done ticket referenced as a blocker must still
    read as closed, not as an unknown/open blocker (T-0096)."""
    active_loaded = load_all(root)
    if active_loaded.is_err:
        return Err(active_loaded.danger_err)
    archived_loaded = load_archive(root)
    if archived_loaded.is_err:
        return Err(archived_loaded.danger_err)
    active, archived = active_loaded.danger_ok, archived_loaded.danger_ok
    overlap = set(active) & set(archived)
    if overlap:
        _log.error("tickets: id(s) %s present in both active and archive", overlap)
        return Err(TicketError.DuplicateId)
    return Ok({**archived, **active})


# frob:invariant INV-004
# frob:doc docs/modules/tickets.md#public-api
def load_queue(root: Path) -> Result[TicketQueue, TicketError]:
    """Load every ticket, active store AND archive merged (malformation in
    either is a hard Err) -- the resolution source for blocker/parent
    lookups and gate joins, so an archived ticket never looks unknown."""
    merged = _load_merged(root)
    if merged.is_err:
        return Err(merged.danger_err)
    tickets = merged.danger_ok
    _log.debug(
        "tickets: loaded %d ticket(s) (active+archive) under %s", len(tickets), root
    )
    return Ok(TicketQueue(tickets=tickets))


# frob:doc docs/modules/tickets.md#public-api
def migrate(root: Path) -> Result[int, TicketError]:
    """Collapse legacy tickets/*.md files into the single tickets.md ledger."""
    return migrate_to_ledger(root)


# frob:doc docs/modules/tickets.md#public-api
# frob:waive TEST005 reason="archive 75.0% branch cover, debt T-0160"
def archive(root: Path) -> Result[int, TicketError]:
    """Move every done/dropped ticket from the active store into
    tickets-archive.md, verbatim (same section format, still tracked and
    greppable); the active ledger keeps only open work. Idempotent -- a
    second call with nothing newly done/dropped moves nothing and returns
    Ok(0). Returns the number of tickets moved."""
    active_loaded = load_all(root)
    if active_loaded.is_err:
        return Err(active_loaded.danger_err)
    active = active_loaded.danger_ok

    to_archive = {
        tid: t
        for tid, t in active.items()
        if t.state in (TicketState.DONE, TicketState.DROPPED)
    }
    if not to_archive:
        _log.info("tickets: archive -- nothing to move")
        return Ok(0)

    archived_loaded = load_archive(root)
    if archived_loaded.is_err:
        return Err(archived_loaded.danger_err)
    archived = archived_loaded.danger_ok

    overlap = set(to_archive) & set(archived)
    if overlap:
        _log.error("tickets: archive id collision %s", overlap)
        return Err(TicketError.DuplicateId)

    archive_write = write_archive(root, {**archived, **to_archive})
    if archive_write.is_err:
        return Err(archive_write.danger_err)

    keep = {tid: t for tid, t in active.items() if tid not in to_archive}
    active_write = write_all(root, keep)
    if active_write.is_err:
        return Err(active_write.danger_err)

    _log.info("tickets: archived %d ticket(s)", len(to_archive))
    return Ok(len(to_archive))


# frob:ticket T-0162
# frob:doc docs/modules/tickets.md#decision-record-t-0162
def _allocate_ticket_id(
    root: Path, existing: dict[str, Ticket], merged: dict[str, Ticket]
) -> str:
    """The id a fresh ticket should get: the next sequential T-#### when
    `root` is on the default branch (the merged view is authoritative there),
    otherwise a provisional T-draft-<hex> id -- final sequential ids are only
    ever minted against the default branch's view, so two checkouts filing
    independently structurally cannot converge on the same final id (T-0162:
    three real collisions were all sequential max+1 races across checkouts).
    """
    if not on_default_branch(root):
        draft_id = mint_draft_id()
        while draft_id in existing or draft_id in merged:
            draft_id = mint_draft_id()
        _log.info("tickets: off-default-branch, minted provisional id %s", draft_id)
        return draft_id
    return _next_ticket_id(merged)


def _next_ticket_id(existing: dict[str, Ticket]) -> str:
    """The next sequential `T-####` id above the highest existing ticket number
    in `existing` -- callers must pass the id space they want ids kept clear
    of (T-0140: `new_ticket` passes active+archive merged, not active alone)."""
    max_num = 0
    for tid in existing:
        try:
            max_num = max(max_num, int(tid.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return f"T-{max_num + 1:04d}"


def _ticket_from_spec(
    ticket_id: str, spec: TicketSpec, evidence: tuple[str, ...]
) -> Ticket:
    """Build a fresh QUEUED ticket from `spec`, applying the incident template."""
    body = spec.body
    if spec.kind == TicketKind.INCIDENT and not body.strip():
        body = _INCIDENT_TEMPLATE
    return Ticket(
        id=ticket_id,
        title=spec.title,
        state=TicketState.QUEUED,
        kind=spec.kind,
        origin=spec.origin,
        created=date.today(),
        blocked_by=spec.blocked_by,
        parent=spec.parent,
        scope=spec.scope,
        evidence=evidence,
        attachments=(),
        acceptance=spec.acceptance,
        threat=spec.threat,
        body=body,
    )


# frob:ticket T-0102
# frob:ticket T-0140
# frob:doc docs/modules/tickets.md#public-api
# frob:waive TEST005 reason="new_ticket 80.0% branch cover, debt T-0160"
def new_ticket(root: Path, spec: TicketSpec) -> Result[Ticket, TicketError]:
    """Allocate the next sequential id and upsert the ticket into the store.

    Any `spec.evidence` entries are schema-validated (validate_evidence)
    before the ticket is ever built, so a malformed entry cannot land via
    `frob ticket new` either (T-0102 companion fix). The id is allocated from
    the max across BOTH the active ledger and the archive (T-0140) -- scanning
    only the active store restarts numbering at T-0001 the moment a queue has
    been archived, colliding with archived ids and making the merged queue
    unloadable (DuplicateId) on the very next `load_queue`. A malformed
    archive fails loudly here too, via the same `_load_merged` path
    `load_queue` uses -- never silently ignored.
    """
    validated = _validate_evidence_list(spec.evidence)
    if validated.is_err:
        return Err(validated.danger_err)
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    existing = loaded.danger_ok
    merged = _load_merged(root)
    if merged.is_err:
        _log.error("tickets: id allocation aborted, archive unreadable")
        return Err(merged.danger_err)
    ticket_id = _allocate_ticket_id(root, existing, merged.danger_ok)
    if ticket_id in existing:
        _log.error("tickets: id collision allocating %s", ticket_id)
        return Err(TicketError.DuplicateId)
    ticket = _ticket_from_spec(ticket_id, spec, validated.danger_ok)
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


def _is_contiguous(ordered: list[Ticket], mapping: dict[str, str]) -> bool:
    """Whether every ticket already carries the id `mapping` would assign it."""
    return all(t.id == mapping[t.id] for t in ordered)


def _apply_renumber(
    ordered: list[Ticket], mapping: dict[str, str]
) -> tuple[dict[str, Ticket], int]:
    """Rewrite each ticket's id plus blocked_by/parent refs via `mapping`."""

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
    return new_map, renumbered


# frob:doc docs/modules/tickets.md#public-api
# frob:waive TEST005 reason="renumber 69.2% branch cover, debt T-0160"
def renumber(root: Path) -> Result[int, TicketError]:
    """Reassign ticket ids to a contiguous T-0001.. sequence (ordered by
    current id), rewriting blocked_by/parent references so the queue stays
    consistent. The remedy for sequential-id collisions after a worktree
    merge (T-0012). Returns the number of tickets renumbered.
    """
    loaded = load_all(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ordered = sorted(loaded.danger_ok.values(), key=lambda t: t.id)
    mapping = {t.id: f"T-{i + 1:04d}" for i, t in enumerate(ordered)}
    if _is_contiguous(ordered, mapping):
        _log.info("tickets: renumber -- already contiguous, nothing to do")
        return Ok(0)
    new_map, renumbered = _apply_renumber(ordered, mapping)
    result = write_all(root, new_map)
    if result.is_err:
        return Err(result.danger_err)
    _log.info("tickets: renumbered %d ticket(s)", renumbered)
    return Ok(renumbered)


_DIRECTIVE_LINE_RE = re.compile(r"frob:(ticket|waive|todo|tests|invariant|doc)\b")
_SKIP_DIR_NAMES = frozenset(
    {".git", ".venv", "node_modules", "__pycache__", ".frob", "target", "dist", "build"}
)


def _tracked_files(root: Path) -> list[Path]:
    """Every git-tracked file under `root`, or (no git repo) every file not
    under a build/vendor/cache directory -- the search space `renumber_one`
    scans for code directive references. Falling back to a filesystem walk
    keeps renumber usable in a non-git fixture/test tree."""
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "ls-files"])
    if spawned.is_ok and spawned.danger_ok.returncode == 0:
        return [root / line for line in spawned.danger_ok.stdout.splitlines() if line]
    files: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and not any(part in _SKIP_DIR_NAMES for part in path.parts):
            files.append(path)
    return files


def _rewrite_directive_references(
    text: str, old_id: str, new_id: str
) -> tuple[str, int]:
    """Replace whole-word `old_id` with `new_id` on every line that carries a
    `frob:` directive -- never elsewhere in the file (a ticket id mentioned
    in prose/a docstring/an unrelated string is left alone; only directive
    lines are code REFERENCES this command owns rewriting)."""
    id_re = re.compile(rf"\b{re.escape(old_id)}\b")
    lines = text.splitlines(keepends=True)
    hits = 0
    for i, line in enumerate(lines):
        if _DIRECTIVE_LINE_RE.search(line) and id_re.search(line):
            lines[i], n = id_re.subn(new_id, line)
            hits += n
    return "".join(lines), hits


def _scan_code_references(
    root: Path, old_id: str, new_id: str
) -> dict[Path, tuple[str, int]]:
    """Every tracked non-ledger file whose directive lines mention `old_id`,
    mapped to its rewritten text and the number of references replaced."""
    skip_names = {ledger_path(root).name, archive_path(root).name}
    changed: dict[Path, tuple[str, int]] = {}
    for path in _tracked_files(root):
        if path.name in skip_names:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if old_id not in text:
            continue
        rewritten, hits = _rewrite_directive_references(text, old_id, new_id)
        if hits:
            changed[path] = (rewritten, hits)
    return changed


# frob:ticket T-0162
# frob:doc docs/modules/tickets.md#public-api
# frob:waive TEST005 reason="renumber_one 68.3% branch cover, debt T-0160"
def renumber_one(
    root: Path, old_id: str, new_id: str, *, dry_run: bool = False
) -> Result[RenumberReport, TicketError]:
    """Atomically rewrite ONE ticket's id everywhere: its ledger section
    (active or archive, id + every blocked_by/parent reference across BOTH
    stores) and every `frob:ticket`/`frob:waive`/`frob:todo`/`frob:tests`/
    `frob:invariant`/`frob:doc` directive line across the tracked tree that
    names it. First-class replacement for the hand-run sed that fixed the
    T-0157 incident's ~100 stray waiver references -- a single command,
    `--dry-run`-able, that can never miss a reference class the old sed
    invocation didn't happen to cover. Also the rename primitive
    `finalize_draft` (T-0162's provisional-id mechanism) and, later,
    T-0176's `frob ticket land` reuse.
    """
    if old_id == new_id:
        _log.warning("tickets: renumber_one %s -> %s is a no-op id", old_id, new_id)
        return Err(TicketError.InvalidTransition)

    active_loaded = load_all(root)
    if active_loaded.is_err:
        return Err(active_loaded.danger_err)
    archived_loaded = load_archive(root)
    if archived_loaded.is_err:
        return Err(archived_loaded.danger_err)
    active_map, archive_map = active_loaded.danger_ok, archived_loaded.danger_ok

    if old_id not in active_map and old_id not in archive_map:
        _log.error("tickets: renumber_one: %s not found", old_id)
        return Err(TicketError.NotFound)
    if new_id in active_map or new_id in archive_map:
        _log.error("tickets: renumber_one: target id %s already exists", new_id)
        return Err(TicketError.DuplicateId)

    all_ids = set(active_map) | set(archive_map)
    full_mapping = {tid: tid for tid in all_ids}
    full_mapping[old_id] = new_id

    new_active_map, active_changed = _apply_renumber(
        list(active_map.values()), full_mapping
    )
    new_archive_map, archive_changed = _apply_renumber(
        list(archive_map.values()), full_mapping
    )
    code_changes = _scan_code_references(root, old_id, new_id)

    report = RenumberReport(
        old_id=old_id,
        new_id=new_id,
        ledger_changed=bool(active_changed or archive_changed),
        files_changed=tuple(sorted(str(p.relative_to(root)) for p in code_changes)),
        occurrences=sum(hits for _text, hits in code_changes.values()),
        dry_run=dry_run,
    )
    if dry_run:
        _log.info(
            "tickets: renumber_one DRY RUN %s -> %s: ledger_changed=%s "
            "code_files=%d occurrences=%d",
            old_id,
            new_id,
            report.ledger_changed,
            len(report.files_changed),
            report.occurrences,
        )
        return Ok(report)

    if active_changed:
        write_result = write_all(root, new_active_map)
        if write_result.is_err:
            return Err(write_result.danger_err)
    if archive_changed:
        archive_write = write_archive(root, new_archive_map)
        if archive_write.is_err:
            return Err(archive_write.danger_err)
    for path, (rewritten, _hits) in code_changes.items():
        written = atomic_write(path, rewritten)
        if written.is_err:
            return Err(written.danger_err)

    _log.info(
        "tickets: renumbered %s -> %s (%d code file(s), %d reference(s) updated)",
        old_id,
        new_id,
        len(code_changes),
        report.occurrences,
    )
    return Ok(report)


# frob:ticket T-0162
# frob:doc docs/modules/tickets.md#provisional-ids
# frob:waive TEST005 reason="finalize_draft 64.7% branch cover, debt T-0160"
def finalize_draft(root: Path, draft_id: str) -> Result[str, TicketError]:
    """Assign `draft_id` its final sequential `T-####` id against the CURRENT
    merged (active+archive) view and rewrite the ledger plus every code
    reference via `renumber_one`. This is the callable finalize step the
    T-0162 provisional-id mechanism promises T-0176 (`frob ticket land`):
    a land/merge command finalizes a draft id by calling this function once
    the draft has actually landed on the default branch -- never before,
    since finalizing against a stale (pre-merge) view can reintroduce the
    exact collision this mechanism exists to prevent. A no-op (`Ok(draft_id)`
    unchanged) if `draft_id` is already a final id, so callers can call it
    unconditionally without checking `is_draft_id` themselves first.
    """
    if not is_draft_id(draft_id):
        _log.debug("tickets: finalize_draft(%s): already final, no-op", draft_id)
        return Ok(draft_id)
    merged = _load_merged(root)
    if merged.is_err:
        return Err(merged.danger_err)
    tickets = merged.danger_ok
    if draft_id not in tickets:
        _log.error("tickets: finalize_draft: %s not found", draft_id)
        return Err(TicketError.NotFound)
    final_id = _next_ticket_id(
        {tid: t for tid, t in tickets.items() if tid != draft_id}
    )
    result = renumber_one(root, draft_id, final_id)
    if result.is_err:
        return Err(result.danger_err)
    _log.info("tickets: finalized draft %s -> %s", draft_id, final_id)
    return Ok(final_id)


def _doable_candidates(queue: TicketQueue) -> list[Ticket]:
    """Queued/planned tickets that currently have no open blockers, unordered."""
    return [
        t
        for t in queue.tickets.values()
        if t.state in (TicketState.QUEUED, TicketState.PLANNED)
        and not _open_blockers(queue, t)
    ]


# frob:doc docs/modules/tickets.md#public-api
def doable(queue: TicketQueue) -> tuple[Ticket, ...]:
    """Tickets in {queued, planned} with no open blockers, ordered oldest-first."""
    candidates = _doable_candidates(queue)
    return tuple(sorted(candidates, key=lambda t: (t.created, t.id)))


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


_MAX_EVIDENCE_LEN = 300


# frob:ticket T-0102
# frob:doc docs/modules/tickets.md#public-api
def validate_evidence(entry: str) -> Result[str, TicketError]:
    """One evidence string's schema: non-empty, single-line, bounded length.

    Writers (`new_ticket`, `add_evidence`) call this before a Ticket ever
    reaches `write_ticket`, so a malformed entry is rejected in-process
    instead of landing as broken YAML that only surfaces later when
    `load_queue` (and therefore every `frob check` gate) fails to parse it
    (T-0102 companion fix -- the vacuous-pass class started with a hand-
    edited evidence block that bypassed this validation entirely).
    """
    stripped = entry.strip()
    if not stripped:
        _log.warning("tickets: rejected empty evidence entry")
        return Err(TicketError.MalformedEvidence)
    if "\n" in entry or "\r" in entry:
        _log.warning("tickets: rejected multi-line evidence entry %r", entry)
        return Err(TicketError.MalformedEvidence)
    if len(stripped) > _MAX_EVIDENCE_LEN:
        _log.warning(
            "tickets: rejected evidence entry over %d chars", _MAX_EVIDENCE_LEN
        )
        return Err(TicketError.MalformedEvidence)
    return Ok(stripped)


def _validate_evidence_list(
    entries: tuple[str, ...],
) -> Result[tuple[str, ...], TicketError]:
    """Validate every entry in `entries`, or the first schema failure."""
    validated: list[str] = []
    for entry in entries:
        result = validate_evidence(entry)
        if result.is_err:
            return Err(result.danger_err)
        validated.append(result.danger_ok)
    return Ok(tuple(validated))


# frob:ticket T-0102
# frob:doc docs/modules/tickets.md#public-api
def _has_done_report(body: str) -> bool:
    """Whether body contains a '## Done report' section heading."""
    return any(line.strip() == _DONE_REPORT_HEADING for line in body.splitlines())


def _start_blockers(ticket: Ticket, queue: dict[str, Ticket]) -> list[str]:
    """Blocker ids of `ticket` that are unknown or still in an open state."""
    return [
        b for b in ticket.blocked_by if b not in queue or queue[b].state in _OPEN_STATES
    ]


def _transition_guard(
    ticket: Ticket, to: TicketState, queue: dict[str, Ticket]
) -> Result[None, TicketError]:
    """Enforce start-blocker and done-evidence preconditions for `to`."""
    if to == TicketState.IN_PROGRESS:
        open_ids = _start_blockers(ticket, queue)
        if open_ids:
            _log.warning(
                "tickets: %s cannot start, open blockers %s", ticket.id, open_ids
            )
            return Err(TicketError.BlockerOpen)
    if to == TicketState.DONE and (
        not ticket.evidence or not _has_done_report(ticket.body)
    ):
        _log.warning(
            "tickets: %s cannot close, missing evidence or Done report", ticket.id
        )
        return Err(TicketError.MissingEvidence)
    return Ok(None)


# frob:invariant INV-002
# frob:doc docs/modules/tickets.md#public-api
def transition(
    root: Path, ticket_id: str, to: TicketState
) -> Result[Ticket, TicketError]:
    """Enforce the state machine; `done` also requires evidence and a Done report."""
    # Blocker resolution needs archived tickets too (a blocker archived
    # after `done` must still read as closed, not unknown/open) -- the
    # ticket being transitioned itself is always still in the active store
    # (archived tickets are done/dropped, terminal, so a lookup that only
    # ever finds one there fails the state machine correctly, T-0096).
    loaded = _load_merged(root)
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

    guard = _transition_guard(ticket, to, queue)
    if guard.is_err:
        return Err(guard.danger_err)

    updated = ticket.model_copy(update={"state": to})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info("tickets: %s transitioned %s -> %s", ticket_id, ticket.state, to)
    return Ok(updated)


def _matches_collected(evidence: str, collected: frozenset[str]) -> bool:
    """Exact node-id membership, or bare-function match for parametrized tests
    (`f` satisfies evidence when only `f[param]` variants were collected).
    Mirrors frob.gates._evidence_collected -- deliberately duplicated (not
    imported) so frob.tickets stays free of the frob.graph dependency that
    module would pull in (docs/rework.md cycle-avoidance)."""
    if evidence in collected:
        return True
    prefix = evidence + "["
    return any(node.startswith(prefix) for node in collected)


# frob:doc docs/modules/tickets.md#public-api
def add_evidence(
    root: Path,
    ticket_id: str,
    node_ids: Sequence[str],
    collected: frozenset[str] | None = None,
) -> Result[Ticket, TicketError]:
    """Validate `node_ids` against `collected` pytest node ids and append the
    resolvable ones to the ticket's structured evidence list; rejecting the
    whole batch (Err(UnknownEvidence)) if any id is unresolvable, so a typo'd
    id can never sneak into evidence and surface only at close time as
    COV003 (the failure mode this command exists to close at write time).
    `collected` is supplied by the caller (frob.testing.collect_python_tests)
    rather than fetched here, keeping this library free of the frob.graph
    dependency frob.testing pulls in. `collected=None` skips resolution
    (schema validation still applies) -- the T-0102 in-process path where
    no collector is available."""
    validated = _validate_evidence_list(tuple(node_ids))
    if validated.is_err:
        return Err(validated.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    unresolved = (
        []
        if collected is None
        else [nid for nid in node_ids if not _matches_collected(nid, collected)]
    )
    if unresolved:
        _log.warning(
            "tickets: %s evidence rejected, unresolved id(s) %s "
            "(run `frob test --collect` to refresh, or fix the id)",
            ticket_id,
            unresolved,
        )
        return Err(TicketError.UnknownEvidence)

    merged = ticket.evidence + tuple(
        nid for nid in node_ids if nid not in ticket.evidence
    )
    updated = ticket.model_copy(update={"evidence": merged})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info(
        "tickets: %s recorded %d evidence id(s) (%d total)",
        ticket_id,
        len(node_ids),
        len(updated.evidence),
    )
    return Ok(updated)


# frob:doc docs/modules/tickets.md#public-api
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
# frob:waive TEST005 reason="attach 87.5% branch cover, debt T-0160"
def attach(
    root: Path, ticket_id: str, source: AttachmentSource, caption: str
) -> Result[Attachment, AttachError]:
    """Copy a file (or clipboard image) into tickets/attachments/<id>/ and record it."""
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
    """The next `NN-slug.ext` attachment path under the ticket's attachment dir."""
    dest_dir = attachments_dir(root, ticket_id)
    existing = sorted(dest_dir.glob("[0-9][0-9]-*")) if dest_dir.exists() else []
    next_index = len(existing) + 1
    return dest_dir / f"{next_index:02d}-{slugify(caption)}{suffix}"


def _record_attachment(
    root: Path, ticket: Ticket, dest_path: Path, caption: str, sha256: str
) -> Result[Attachment, AttachError]:
    """Append the written attachment to `ticket` and persist the ticket."""
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


__all__ = [
    "Attachment",
    "AttachError",
    "AttachmentSource",
    "ClipboardError",
    "FailureEntry",
    "LandError",
    "LandReport",
    "Origin",
    "Ticket",
    "TicketError",
    "TicketKind",
    "TicketQueue",
    "TicketSpec",
    "TicketState",
    "add_evidence",
    "archive",
    "attach",
    "doable",
    "land",
    "load_active",
    "load_queue",
    "Stride",
    "migrate",
    "new_ticket",
    "renumber",
    "record_failure",
    "splice_ledger",
    "transition",
    "validate_evidence",
]

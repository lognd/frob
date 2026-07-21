"""
frob.tickets -- statically-checkable ticket and feature queue (docs/modules/tickets.md).

A git-tracked queue of tickets (features, bugs, audits, invariant work) with
a state machine, blockers, evidence, failure memory, and image attachments --
the shared work surface for the human and every agent. No dependency on
frob.graph or frob.lang by design (see docs/rework.md cycle-avoidance).
"""

from __future__ import annotations

import fnmatch
import getpass
import hashlib
import re
import subprocess
import tomllib
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._land import land, splice_ledger
from frob.tickets._leases import read_all_leases
from frob.tickets._models import (
    CMD_EVIDENCE_ALLOWED_KINDS,
    DONE_REPORT_HEADING,
    LEDGER_PATH,
    OVER_BROAD_LITERAL_GLOBS,
    Attachment,
    AttachmentSource,
    FailureEntry,
    LandError,
    LandReport,
    Origin,
    RenumberReport,
    ScopeChangeEntry,
    ScopeChangeOp,
    Stride,
    Ticket,
    TicketError,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
    has_substantive_done_report,
    is_cmd_evidence,
    matches_collected,
    replace_done_report_section,
    scope_matches,
    scope_overlap_globs,
)
from frob.tickets._models import _split_scope_entries as _normalize_scope_entries
from frob.tickets._provisional import is_draft_id, mint_draft_id, on_default_branch
from frob.tickets._store import (
    archive_path,
    atomic_write,
    attachments_dir,
    ledger_lock,
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
from frob.tickets.clipboard import ClipboardError, clipboard_has_image, clipboard_image

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
# invariant spec: [INV-004](invariants/INV-004.md)
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

    return _write_archived_and_active(root, active, to_archive)


def _write_archived_and_active(
    root: Path, active: dict[str, Ticket], to_archive: dict[str, Ticket]
) -> Result[int, TicketError]:
    """Merge `to_archive` into the archive file and drop it from the active
    ledger, in that order; `Err(DuplicateId)` on an id already archived."""
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
# frob:ticket T-0398
# frob:doc docs/modules/tickets.md#public-api
# frob:waive TEST005 reason="new_ticket 80.0% branch cover, debt T-0160"
def new_ticket(
    root: Path,
    spec: TicketSpec,
    collected: frozenset[str] | None = None,
) -> Result[Ticket, TicketError]:
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

    D-08: `spec.evidence` is now ALSO resolution-checked via the same
    `_check_evidence_resolution` `add_evidence` uses, whenever a caller
    supplies `collected` -- previously `new_ticket --evidence` only
    schema-validated, so a bogus id (`tests/ghost.py::test_x`) was stored
    unresolved and surfaced only if/when the ticket later reached DONE and
    `frob check` ran COV003. `collected=None` (default, matching every
    caller before D-08) preserves that schema-only behavior for a context
    with no collector available, but now logs the same explicit UNRESOLVED
    warning `add_evidence` does, so the gap is never silent.
    """
    validated = _validate_evidence_list(spec.evidence)
    if validated.is_err:
        return Err(validated.danger_err)
    resolution = _check_evidence_resolution(
        "new_ticket", validated.danger_ok, collected
    )
    if resolution.is_err:
        return Err(resolution.danger_err)
    # frob:ticket T-0458
    # Allocation (read the current max id) and the write that claims it
    # MUST happen under one held lock -- two processes each reading the
    # pre-write max id and then writing, unlocked in between, is exactly
    # the sequential-id race that produced T-0465's duplicate T-0427.
    # `write_ticket` re-acquires the same lock internally (reentrant, see
    # `ledger_lock`), so this outer hold is what actually closes the gap.
    with ledger_lock(root):
        ticket_id_result = _allocate_and_check_ticket_id(root)
        if ticket_id_result.is_err:
            return Err(ticket_id_result.danger_err)
        ticket_id = ticket_id_result.danger_ok
        ticket = _ticket_from_spec(ticket_id, spec, validated.danger_ok)
        write_result = write_ticket(root, ticket)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: created %s", ticket_id)
    return Ok(ticket)


def _allocate_and_check_ticket_id(root: Path) -> Result[str, TicketError]:
    """Load the active+archived ticket state and allocate a fresh id,
    erroring on an archive-load failure or an id collision."""
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
    return Ok(ticket_id)


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


def _tracked_files(root: Path) -> list[Path]:
    """Every git-tracked file under `root`, or (no git repo) every file not
    under a build/vendor/cache directory -- the search space `renumber_one`
    scans for code directive references. Falling back to a filesystem walk
    keeps renumber usable in a non-git fixture/test tree."""
    from frob.excludes import iter_files

    return list(iter_files(root))


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


def _load_and_validate_renumber_ids(
    root: Path, old_id: str, new_id: str
) -> Result[tuple[dict[str, Ticket], dict[str, Ticket]], TicketError]:
    """Load the active+archive ledgers and validate `old_id`/`new_id` are
    renumber-able: not equal, `old_id` present, `new_id` free."""
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
    return Ok((active_map, archive_map))


def _persist_renumber(
    root: Path,
    *,
    new_active_map: dict[str, Ticket],
    active_changed: int,
    new_archive_map: dict[str, Ticket],
    archive_changed: int,
    code_changes: dict[Path, tuple[str, int]],
) -> Result[None, TicketError]:
    """Write back the renumbered active/archive ledgers (if changed) and
    every rewritten code-reference file."""
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
    return Ok(None)


def _apply_renumber_mapping(
    active_map: dict[str, Ticket],
    archive_map: dict[str, Ticket],
    old_id: str,
    new_id: str,
) -> tuple[dict[str, Ticket], int, dict[str, Ticket], int]:
    """Build the id-rename mapping (`old_id -> new_id`, every other id
    fixed) and apply it to both the active and archive ticket maps."""
    all_ids = set(active_map) | set(archive_map)
    full_mapping = {tid: tid for tid in all_ids}
    full_mapping[old_id] = new_id

    new_active_map, active_changed = _apply_renumber(
        list(active_map.values()), full_mapping
    )
    new_archive_map, archive_changed = _apply_renumber(
        list(archive_map.values()), full_mapping
    )
    return new_active_map, active_changed, new_archive_map, archive_changed


def _build_renumber_report(
    root: Path,
    old_id: str,
    new_id: str,
    active_changed: int,
    archive_changed: int,
    code_changes: dict[Path, tuple[str, int]],
    dry_run: bool,
) -> RenumberReport:
    """Assemble the `RenumberReport` for a rename, from the computed
    ledger-changed flags and code-reference scan results."""
    return RenumberReport(
        old_id=old_id,
        new_id=new_id,
        ledger_changed=bool(active_changed or archive_changed),
        files_changed=tuple(sorted(str(p.relative_to(root)) for p in code_changes)),
        occurrences=sum(hits for _text, hits in code_changes.values()),
        dry_run=dry_run,
    )


def _log_renumber_dry_run(old_id: str, new_id: str, report: RenumberReport) -> None:
    """Log the DRY RUN summary line for `renumber_one`."""
    _log.info(
        "tickets: renumber_one DRY RUN %s -> %s: ledger_changed=%s "
        "code_files=%d occurrences=%d",
        old_id,
        new_id,
        report.ledger_changed,
        len(report.files_changed),
        report.occurrences,
    )


# First-class replacement for the hand-run sed that fixed the T-0157
# incident's ~100 stray waiver references -- a single command,
# `--dry-run`-able, that can never miss a reference class the old sed
# invocation didn't happen to cover. Also the rename primitive
# `finalize_draft` (T-0162's provisional-id mechanism) and, later,
# T-0176's `frob ticket land` reuse.
# frob:doc docs/modules/tickets.md#public-api
# frob:ticket T-0162
# frob:waive TEST005 reason="renumber_one 68.3% branch cover, debt T-0160"
def renumber_one(
    root: Path, old_id: str, new_id: str, *, dry_run: bool = False
) -> Result[RenumberReport, TicketError]:
    """Atomically rewrite ONE ticket's id everywhere: its ledger section
    (active or archive, id + every blocked_by/parent reference across BOTH
    stores) and every `frob:ticket`/`frob:waive`/`frob:todo`/`frob:tests`/
    `frob:invariant`/`frob:doc` directive line across the tracked tree that
    names it."""
    loaded = _load_and_validate_renumber_ids(root, old_id, new_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    active_map, archive_map = loaded.danger_ok
    new_active_map, active_changed, new_archive_map, archive_changed = (
        _apply_renumber_mapping(active_map, archive_map, old_id, new_id)
    )
    code_changes = _scan_code_references(root, old_id, new_id)
    report = _build_renumber_report(
        root, old_id, new_id, active_changed, archive_changed, code_changes, dry_run
    )
    if dry_run:
        _log_renumber_dry_run(old_id, new_id, report)
        return Ok(report)

    persisted = _persist_renumber(
        root,
        new_active_map=new_active_map,
        active_changed=active_changed,
        new_archive_map=new_archive_map,
        archive_changed=archive_changed,
        code_changes=code_changes,
    )
    return _finish_renumber(persisted, old_id, new_id, code_changes, report)


def _finish_renumber(
    persisted: Result[None, TicketError],
    old_id: str,
    new_id: str,
    code_changes: dict[Path, tuple[str, int]],
    report: RenumberReport,
) -> Result[RenumberReport, TicketError]:
    """Propagate a persist failure, else log completion and return the report."""
    if persisted.is_err:
        return Err(persisted.danger_err)
    _log_renumber_done(old_id, new_id, code_changes, report)
    return Ok(report)


def _log_renumber_done(
    old_id: str,
    new_id: str,
    code_changes: dict[Path, tuple[str, int]],
    report: RenumberReport,
) -> None:
    """Log the completed-rename summary line for `renumber_one`."""
    _log.info(
        "tickets: renumbered %s -> %s (%d code file(s), %d reference(s) updated)",
        old_id,
        new_id,
        len(code_changes),
        report.occurrences,
    )


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


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
def _in_progress_leases(queue: TicketQueue) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """`(ticket_id, scope)` for every IN_PROGRESS ticket, id-ordered -- the
    active scope-leases `doable`'s default collision filter and
    `leased_by`'s explanation both check candidates against (T-0453
    scope-lease model)."""
    return tuple(
        (t.id, t.scope)
        for t in sorted(queue.tickets.values(), key=lambda t: t.id)
        if t.state is TicketState.IN_PROGRESS
    )


# frob:ticket T-0473
def _cross_worktree_leases(
    queue: TicketQueue, root: Path
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """`(ticket_id, scope)` for every lease `frob.tickets._leases` reports
    from ANY worktree of `root`'s repository (T-0473) -- the fix for the
    T-0453 lease model being inert across worktrees, since a ticket started
    in an isolated worktree never reaches THIS worktree's own
    `tickets.md`. A lease whose ticket id the LOCAL ledger already shows as
    `DONE`/`DROPPED` is dropped as stale (a crashed worktree's unreleased
    lease for an already-finished ticket must not block `doable` forever;
    full liveness reconciliation across worktrees is T-0476's job, this is
    only a cheap local-ledger staleness guard, not a substitute for it)."""
    leases = read_all_leases(root)
    kept: list[tuple[str, tuple[str, ...]]] = []
    for lease in leases:
        local = queue.tickets.get(lease.ticket_id)
        if local is not None and local.state in (TicketState.DONE, TicketState.DROPPED):
            continue
        kept.append((lease.ticket_id, lease.scope))
    return tuple(kept)


# frob:ticket T-0473
def _all_leases(
    queue: TicketQueue, root: Path | None
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """`_in_progress_leases(queue)` (the local ledger's own view) UNIONED
    with `_cross_worktree_leases` (every OTHER worktree's recorded lease),
    deduplicated by ticket id with the LOCAL ledger's entry always winning
    (it is authoritative for any ticket this worktree's own `tickets.md`
    already knows about) (T-0473). `root=None` (no repo to consult the
    shared lease directory from -- e.g. a caller with no filesystem root)
    keeps the exact pre-T-0473 local-only behavior."""
    local = _in_progress_leases(queue)
    if root is None:
        return local
    merged: dict[str, tuple[str, ...]] = dict(local)
    for ticket_id, scope in _cross_worktree_leases(queue, root):
        merged.setdefault(ticket_id, scope)
    return tuple(sorted(merged.items()))


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
_LARGE_GLOB_DEFAULT_MAX_FILES = 25


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
def _load_large_glob_max_files(root: Path) -> int:
    """Read `[tickets] large_glob_max_files` from `frob.toml` -- the
    tunable file-count threshold `large_glob_warnings`/`leased_by` flag a
    scope glob against (T-0453). Absent config, an unreadable/malformed
    file, or a non-positive value all fall back to
    `_LARGE_GLOB_DEFAULT_MAX_FILES` rather than erroring, matching
    `frob.excludes.load_exclude_globs`'s degrade-quietly posture for
    optional config."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return _LARGE_GLOB_DEFAULT_MAX_FILES
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("tickets: could not parse %s: %s", toml_path, exc)
        return _LARGE_GLOB_DEFAULT_MAX_FILES
    value = doc.get("tickets", {}).get("large_glob_max_files")
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        return _LARGE_GLOB_DEFAULT_MAX_FILES
    return value


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
def _is_excluded_breadth_path(path: str) -> bool:
    """Whether `path` should never count toward the T-0453 breadth measure
    regardless of tracking status -- `.git`/`.venv`/`__pycache__`/... (any
    `frob.excludes.is_skipped_dir` name) and `.claude/worktrees/` (the
    per-agent worktree tree, ~129 of them observed in this repo, whose
    file count would otherwise massively over-count breadth and -- before
    this fix -- made `_repo_files`'s old full-tree `rglob` walk take
    minutes per call)."""
    from frob.excludes import is_skipped_dir

    parts = path.split("/")
    if any(is_skipped_dir(part) for part in parts[:-1]):
        return True
    return path.startswith(".claude/worktrees/")


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
def _repo_files_git(root: Path) -> tuple[str, ...] | None:
    """`git ls-files` under `root` -- tracked files only, `root`-relative
    posix paths, breadth-excluded paths dropped -- or `None` if `root` is
    not a git work tree / `git` is unavailable (T-0453 perf fix: this
    replaces a full-tree `rglob` walk, which used to include the ~129
    stale worktrees under `.claude/worktrees/` and made `frob ticket
    doable` take minutes)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.warning("tickets: git ls-files failed under %s: %s", root, exc)
        return None
    if result.returncode != 0:
        return None
    return tuple(
        sorted(
            line
            for line in result.stdout.splitlines()
            if line and not _is_excluded_breadth_path(line)
        )
    )


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
def _repo_files_walk_fallback(root: Path) -> tuple[str, ...]:
    """Every real file under `root` as `root`-relative posix paths, with
    built-in skip dirs (`.git`, `.venv`, `__pycache__`, ...) and
    `.claude/worktrees/` pruned -- the `_repo_files` fallback for a `root`
    that is not a git work tree (T-0453). Never the default path in a real
    git checkout; `_repo_files_git` is."""
    from frob.excludes import walk_pruned

    files: list[str] = []
    for path in sorted(walk_pruned(root)):
        rel = path.relative_to(root).as_posix()
        if _is_excluded_breadth_path(rel):
            continue
        files.append(rel)
    return tuple(files)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
def _repo_files(root: Path) -> tuple[str, ...]:
    """The T-0453 breadth-check file universe under `root`: `git ls-files`
    (tracked files, fast) when `root` is a git work tree, else a pruned
    tree walk (`_repo_files_walk_fallback`). Callers should invoke this
    (via `scope_breadth_context`) ONCE per `doable` call, never once per
    candidate x holder pair -- see `scope_breadth_context`."""
    tracked = _repo_files_git(root)
    if tracked is not None:
        return tracked
    return _repo_files_walk_fallback(root)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestBreadthPerf.test_computed_once_per_doable_call  # noqa: E501
def scope_breadth_context(root: Path) -> tuple[int, tuple[str, ...]]:
    """`(large_glob_max_files threshold, repo_files)` computed ONCE -- the
    shared input `_over_broad_scope_entries`/`large_glob_warnings` reuse
    instead of each re-running `git ls-files`/re-walking the tree per
    candidate x holder pair (T-0453 perf fix: this repo's real `frob
    ticket doable` used to take minutes -- a full-tree `rglob`, including
    ~129 stale `.claude/worktrees/` checkouts, called once per candidate
    per in-progress holder). `doable`/`doable_blocked` compute this a
    single time per call and thread it through `leased_by`."""
    return (_load_large_glob_max_files(root), _repo_files(root))


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
def _entry_to_glob(entry: str) -> str:
    """Expand a bare directory-prefix scope entry (`"docs/"`, no wildcard
    metacharacters) into its recursive glob (`"docs/**"`) -- the SAME
    expansion `frob.tickets._models._scope_globs` applies, duplicated here
    (rather than imported) only because this needs the single-entry form
    to build a per-entry warning/breadth message; `_scope_globs` itself
    remains the one place actual scope MATCHING expands from (T-0453)."""
    if entry.endswith("/") and not any(ch in entry for ch in "*?["):
        return entry + "**"
    return entry


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
def _over_broad_scope_entries(
    scope: Sequence[str], threshold: int, files: Sequence[str]
) -> tuple[str, ...]:
    """Declared scope entries of `scope` that are over-broad (T-0453): a
    named chronically-broad glob (`OVER_BROAD_LITERAL_GLOBS`) unconditionally,
    or one matching more of `files` than `threshold`. `LEDGER_PATH` is never
    flagged (every ticket implicitly leases it).

    Takes a PRECOMPUTED `(threshold, files)` pair (`scope_breadth_context`)
    rather than a `root` to walk -- this is the hot inner loop callers run
    once per candidate x holder pair, and re-deriving `files` (a `git
    ls-files`/tree-walk) on every call is exactly the T-0453 perf bug
    (`frob ticket doable` taking minutes on this repo's real worktree
    count) this signature avoids.

    THE single breadth criterion both `large_glob_warnings` (nudge the
    ticket author to narrow it) and `leased_by` (an over-broad in-progress
    lease demotes to warn-only rather than hard-blocking the ENTIRE queue,
    T-0453 real-repo verification) consult -- one signal driving two
    behaviors, not a `tests/**`/`docs/` directory special-case (the fix the
    T-0453 DESIGN CORRECTION explicitly forbids): any glob this broad by
    this SAME measure is treated the same way, regardless of which
    directory it names.
    """
    broad: list[str] = []
    for entry in scope:
        if entry == LEDGER_PATH:
            continue
        if entry in OVER_BROAD_LITERAL_GLOBS:
            broad.append(entry)
            continue
        # fnmatch.filter translates the glob ONCE and matches all files in
        # one pass (T-0453 perf fix: was 624k fnmatch.fnmatch calls
        # re-deriving the same glob per file on the real repo).
        if len(fnmatch.filter(files, _entry_to_glob(entry))) > threshold:
            broad.append(entry)
    return tuple(broad)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestLargeGlobWarnings.test_fires_on_broad_tests_glob  # noqa: E501
# frob:tests tests/test_tickets_lease.py::TestLargeGlobWarnings.test_silent_on_precise_test_file  # noqa: E501
def large_glob_warnings(
    ticket: Ticket,
    root: Path,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> tuple[str, ...]:
    """Human-readable nudges for any of `ticket`'s declared scope entries
    `_over_broad_scope_entries` flags (T-0453 DESIGN CORRECTION). Empty for
    a precisely-scoped ticket (e.g. `tests/test_gates.py`).

    Pass a precomputed `breadth` (`scope_breadth_context(root)`) when
    calling this in a loop over several tickets so the breadth walk runs
    once, not once per ticket (`root` is still required to label warnings
    consistently and for the `breadth is None` single-call convenience
    path, which computes it internally).

    This is a NUDGE, not a hard gate: it exists to fix over-hiding at the
    scope-DECLARATION level (narrow the glob to the files actually
    touched) instead of ignoring `tests/**`/`docs/` in the lease-overlap
    check itself, which the T-0453 design correction says would mask real
    per-file collisions under those trees.
    """
    threshold, files = breadth if breadth is not None else scope_breadth_context(root)
    warnings: list[str] = []
    for entry in _over_broad_scope_entries(ticket.scope, threshold, files):
        if entry in OVER_BROAD_LITERAL_GLOBS:
            warnings.append(
                f"{ticket.id} scope {entry!r} is a chronically over-broad "
                "glob -- narrow it to the specific files this ticket "
                "touches"
            )
            continue
        matched = len(fnmatch.filter(files, _entry_to_glob(entry)))
        warnings.append(
            f"{ticket.id} scope {entry!r} matches {matched} files "
            f"(> {threshold}) -- narrow it to the specific files this "
            "ticket touches"
        )
    return tuple(warnings)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestLeasedBy.test_precise_in_progress_does_not_hide_disjoint  # noqa: E501
# frob:tests tests/test_tickets_lease.py::TestLeasedBy.test_real_source_scope_collision_is_hidden  # noqa: E501
# frob:tests tests/test_tickets_lease.py::TestLeasedBy.test_over_broad_lease_demotes_to_warn_only  # noqa: E501
def leased_by(
    queue: TicketQueue,
    ticket: Ticket,
    root: Path | None = None,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> tuple[tuple[str, str], ...]:
    """`(holding_ticket_id, glob_that_leases_it)` for every IN_PROGRESS
    ticket whose scope-lease overlaps `ticket`'s own scope (T-0453) --
    empty means `ticket` is free to dispatch right now. Powers both
    `doable`'s default exclusion and `--show-blocked`'s per-ticket
    explanation ("T-0xxx held: scope src/frob/gates/** leased by
    in-progress T-0yyy").

    When `root` is given, a holder's OVER-BROAD scope entries
    (`_over_broad_scope_entries`) are dropped before the overlap check --
    an over-broad DECLARED lease demotes to warn-only (`large_glob_warnings`
    still nudges narrowing it) rather than hard-blocking the entire doable
    queue, so one repo-wide `src/frob/**` in-progress ticket cannot zero
    out `doable` for everyone. Precise scope entries on the SAME holder
    still enforce normally -- this is breadth-driven demotion, not a
    directory-specific carve-out, and does not weaken the sound overlap
    test itself (`root=None` keeps the strict, undemoted check, e.g. for
    callers with no repo root to walk).

    Pass a precomputed `breadth` (`scope_breadth_context(root)`) when
    calling this per-candidate in a loop (`doable`/`doable_blocked` do) so
    the breadth walk runs ONCE for the whole call, not once per candidate
    x holder pair (T-0453 perf fix -- this is what made `frob ticket
    doable` take minutes on this repo's real worktree count before the
    fix). Omitting it while `root` is given computes it internally, for
    standalone/test callers.
    """
    if root is not None and breadth is None:
        breadth = scope_breadth_context(root)
    hits: list[tuple[str, str]] = []
    for holder_id, holder_scope in _all_leases(queue, root):
        if holder_id == ticket.id:
            continue
        effective_scope = holder_scope
        if breadth is not None:
            threshold, files = breadth
            broad = frozenset(_over_broad_scope_entries(holder_scope, threshold, files))
            effective_scope = tuple(s for s in holder_scope if s not in broad)
            if not effective_scope:
                continue
        collision = scope_overlap_globs(ticket.scope, effective_scope)
        if collision is not None:
            hits.append((holder_id, collision[1]))
    return tuple(hits)


# frob:ticket T-0455
def _current_actor() -> str:
    """Best-effort identity for a `scope_changes` audit entry's `actor` field
    -- the OS login name, or `"unknown"` if the platform/sandbox refuses to
    report one (never raises)."""
    try:
        return getpass.getuser()
    except OSError:
        return "unknown"


# frob:ticket T-0455
def _scope_add_conflicts(
    glob: str, ticket_id: str, queue: dict[str, Ticket]
) -> tuple[str, str] | None:
    """`(holding_ticket_id, holder_glob)` if `glob` overlaps the declared
    scope of another IN_PROGRESS ticket (T-0453 lease model), or `None` if
    free to lease. Every OTHER in-progress ticket's FULL declared scope is
    checked (not breadth-demoted) -- an explicit `--add` request is a
    stronger claim than a passive `doable` listing, so this never silently
    lets an expansion into a busy over-broad lease through the same
    demotion `leased_by` applies for queue-display purposes."""
    for holder in sorted(queue.values(), key=lambda t: t.id):
        if holder.id == ticket_id or holder.state is not TicketState.IN_PROGRESS:
            continue
        collision = scope_overlap_globs((glob,), holder.scope)
        if collision is not None:
            return (holder.id, collision[1])
    return None


# frob:ticket T-0455
def _scope_remove_orphans_evidence(glob: str, ticket: Ticket) -> bool:
    """Whether removing `glob` from `ticket.scope` would orphan already-
    recorded evidence (T-0455 guardrail): any evidence id whose leading
    `path::` segment `glob` currently covers."""
    for entry in ticket.evidence:
        path = entry.split("::", 1)[0]
        if fnmatch.fnmatch(path, glob):
            return True
    return False


# frob:ticket T-0455
def _validate_scope_request(
    add_globs: tuple[str, ...], remove_globs: tuple[str, ...], reason: str
) -> Result[None, TicketError]:
    """The two request-shape checks `mutate_scope` rejects before ever
    touching the ledger: at least one op, and a non-blank `reason`
    (T-0455)."""
    if not add_globs and not remove_globs:
        _log.error("tickets: scope change requires --add or --remove")
        return Err(TicketError.ScopeChangeEmpty)
    if not reason.strip():
        _log.error("tickets: scope change requires --reason")
        return Err(TicketError.ScopeChangeReasonMissing)
    return Ok(None)


# frob:ticket T-0455
def _validate_scope_mutation(
    ticket_id: str,
    ticket: Ticket,
    queue: dict[str, Ticket],
    add_globs: tuple[str, ...],
    remove_globs: tuple[str, ...],
) -> Result[None, TicketError]:
    """The per-glob FAIL-LOUD checks `mutate_scope` runs against the loaded
    ticket+queue (T-0455): a `remove` glob must be declared and evidence-
    free (`ScopeRemoveNotDeclared`/`ScopeRemoveOrphansEvidence`); an `add`
    glob must not overlap another in-progress ticket's lease
    (`ScopeLeaseConflict`, `_scope_add_conflicts`)."""
    for glob in remove_globs:
        if glob not in ticket.scope:
            _log.error(
                "tickets: %s cannot remove %r, not in declared scope %s",
                ticket_id,
                glob,
                ticket.scope,
            )
            return Err(TicketError.ScopeRemoveNotDeclared)
        if _scope_remove_orphans_evidence(glob, ticket):
            _log.error(
                "tickets: %s cannot remove %r, covers recorded evidence",
                ticket_id,
                glob,
            )
            return Err(TicketError.ScopeRemoveOrphansEvidence)
    for glob in add_globs:
        conflict = _scope_add_conflicts(glob, ticket_id, queue)
        if conflict is not None:
            holder_id, holder_glob = conflict
            _log.error(
                "tickets: %s cannot lease %r: held by in-progress %s (scope %r)",
                ticket_id,
                glob,
                holder_id,
                holder_glob,
            )
            return Err(TicketError.ScopeLeaseConflict)
    return Ok(None)


# frob:ticket T-0455
def _warn_over_broad_adds(
    root: Path, ticket_id: str, add_globs: tuple[str, ...]
) -> None:
    """Log a WARNING (never a rejection) for any `add_globs` entry the
    T-0453 breadth criterion flags -- a nudge, not a hard block (T-0455)."""
    threshold, files = scope_breadth_context(root)
    for glob in add_globs:
        if _over_broad_scope_entries((glob,), threshold, files):
            _log.warning(
                "tickets: %s --add %r is an over-broad glob -- consider "
                "narrowing it to the files this ticket actually touches",
                ticket_id,
                glob,
            )


# frob:ticket T-0455
def _scope_change_entries(
    add_globs: tuple[str, ...], remove_globs: tuple[str, ...], reason: str
) -> tuple[ScopeChangeEntry, ...]:
    """Build one `ScopeChangeEntry` per mutated glob (removes first, then
    adds), all stamped with today's date and the current actor (T-0455)."""
    today = date.today()
    actor = _current_actor()
    return tuple(
        ScopeChangeEntry(
            op=ScopeChangeOp.REMOVE, glob=g, reason=reason, actor=actor, at=today
        )
        for g in remove_globs
    ) + tuple(
        ScopeChangeEntry(
            op=ScopeChangeOp.ADD, glob=g, reason=reason, actor=actor, at=today
        )
        for g in add_globs
    )


# frob:ticket T-0455
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_scope_mutation.py::TestMutateScope.test_add_free_path_granted  # noqa: E501
# frob:tests tests/test_tickets_scope_mutation.py::TestMutateScope.test_add_leased_path_rejected_names_holder  # noqa: E501
# frob:tests tests/test_tickets_scope_mutation.py::TestMutateScope.test_remove_frees_path_for_other_doable  # noqa: E501
def mutate_scope(
    root: Path,
    ticket_id: str,
    *,
    add: Sequence[str] = (),
    remove: Sequence[str] = (),
    reason: str,
) -> Result[Ticket, TicketError]:
    """Formally expand or reduce `ticket_id`'s declared `scope` -- and, since
    the T-0453 tree-lease is DERIVED live from an in-progress ticket's
    `scope` (`_in_progress_leases`), its active tree-lease too, in the same
    atomic write (T-0455). This is the accountable replacement for the
    ad-hoc SCOPE001 waive dodge (T-0176/T-0220 precedent): every mutation
    appends a `ScopeChangeEntry` to the ticket's `scope_changes` audit list
    instead of hiding the expansion behind a waiver comment.

    `add` and `remove` may be combined in one call; `reason` applies to
    every glob mutated by that call. FAILS LOUDLY (`Err`, no partial write)
    per `_validate_scope_request`/`_validate_scope_mutation`'s docstrings --
    notably `ScopeLeaseConflict` when an `add` glob overlaps a path leased
    by ANOTHER in-progress ticket (the error names the holding ticket): an
    agent can never expand into paths another agent is actively writing.
    An over-broad `add` glob is logged at WARNING only (`_warn_over_broad_adds`).

    Held under `ledger_lock` end to end (load, validate, write) so this can
    never interleave with a concurrent ledger mutation (T-0458 single-writer
    invariant) -- no hand-edit of `tickets.md` is ever involved.
    """
    add_globs = _normalize_scope_entries(tuple(add))
    remove_globs = _normalize_scope_entries(tuple(remove))
    request_check = _validate_scope_request(add_globs, remove_globs, reason)
    if request_check.is_err:
        return Err(request_check.danger_err)

    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, queue = loaded.danger_ok

        mutation_check = _validate_scope_mutation(
            ticket_id, ticket, queue, add_globs, remove_globs
        )
        if mutation_check.is_err:
            return Err(mutation_check.danger_err)

        _warn_over_broad_adds(root, ticket_id, add_globs)
        result = _write_scope_mutation(root, ticket, add_globs, remove_globs, reason)
        if result.is_err:
            return Err(result.danger_err)
        updated = result.danger_ok
    # frob:ticket T-0473
    # The cross-worktree lease's recorded scope must never drift from the
    # ledger's once an in-progress ticket's scope changes -- otherwise
    # another worktree's `doable` would keep colliding against (or missing)
    # a stale scope forever.
    if updated.state is TicketState.IN_PROGRESS:
        from frob.tickets._leases import record_lease

        record_lease(root, ticket_id, updated.scope)
    _log.info(
        "tickets: %s scope changed (+%d/-%d): %s",
        ticket_id,
        len(add_globs),
        len(remove_globs),
        reason,
    )
    return Ok(updated)


# frob:ticket T-0455
def _write_scope_mutation(
    root: Path,
    ticket: Ticket,
    add_globs: tuple[str, ...],
    remove_globs: tuple[str, ...],
    reason: str,
) -> Result[Ticket, TicketError]:
    """Compute `ticket`'s new scope + appended audit entries and write it
    (T-0455) -- the final step `mutate_scope` runs once every validation
    check has passed. Caller holds `ledger_lock` already."""
    new_scope = tuple(s for s in ticket.scope if s not in remove_globs)
    for glob in add_globs:
        if glob not in new_scope:
            new_scope += (glob,)
    new_entries = _scope_change_entries(add_globs, remove_globs, reason)
    updated = ticket.model_copy(
        update={
            "scope": new_scope,
            "scope_changes": ticket.scope_changes + new_entries,
        }
    )
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    return Ok(updated)


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestDoable.test_ignore_lease_returns_raw_list
# frob:waive DRIFT001 reason="T-0453 added root/ignore_lease params; frob.lock ack out of scope, no inline-waivable syntax for JSON -- reviewer re-acks at land"  # noqa: E501
def doable(
    queue: TicketQueue, root: Path | None = None, *, ignore_lease: bool = False
) -> tuple[Ticket, ...]:
    """Tickets in {queued, planned} with no open blockers, ordered
    oldest-first.

    By DEFAULT also excludes any candidate whose declared scope overlaps
    an in-progress ticket's active scope-lease (T-0453 scope-lease model,
    `leased_by`) -- two agents dispatched straight off this list can never
    collide on the same files, with no hand-maintained blocklist. Pass
    `root` (the repo root) so an over-broad holder lease demotes to
    warn-only instead of blocking everything (`leased_by`'s `root`
    parameter); omit it only when no repo root is available to walk (the
    check then stays strict/undemoted). Pass `ignore_lease=True`
    (`frob ticket doable --ignore-lease`) for the raw, blocker-only list
    with no collision filtering at all.
    """
    candidates = _doable_candidates(queue)
    if not ignore_lease:
        breadth = scope_breadth_context(root) if root is not None else None
        candidates = [
            t for t in candidates if not leased_by(queue, t, root, breadth=breadth)
        ]
    return tuple(sorted(candidates, key=lambda t: (t.created, t.id)))


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestShowBlocked.test_show_blocked_lists_reasons  # noqa: E501
def doable_blocked(
    queue: TicketQueue,
    root: Path | None = None,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> tuple[tuple[Ticket, tuple[tuple[str, str], ...]], ...]:
    """Doable-candidates hidden by an in-progress scope-lease, paired with
    WHY (`(holding_ticket_id, overlapping_glob)` per collision) -- the data
    `frob ticket doable --show-blocked` renders (T-0453). See `leased_by`
    for what passing `root` does (over-broad-lease demotion) and what
    passing a precomputed `breadth` (`scope_breadth_context(root)`) avoids
    (re-walking the tree when the caller already has one)."""
    candidates = _doable_candidates(queue)
    if root is not None and breadth is None:
        breadth = scope_breadth_context(root)
    blocked: list[tuple[Ticket, tuple[tuple[str, str], ...]]] = []
    for t in sorted(candidates, key=lambda t: (t.created, t.id)):
        hits = leased_by(queue, t, root, breadth=breadth)
        if hits:
            blocked.append((t, hits))
    return tuple(blocked)


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


# frob:ticket T-0293
# frob:doc docs/modules/tickets.md#public-api
def normalize_evidence_separator(entry: str) -> str:
    """Canonicalize a `path::Class.method` (dot) evidence id to the pytest-
    collected `path::Class::method` (double-colon) form.

    T-0282 and T-0217 both had evidence hand-recorded with a dot before the
    final segment (`Class.method`), which never resolves against real
    pytest node ids (`Class::method`) and only surfaces late as a confusing
    COV003 at check time. This rewrites the single dot immediately after
    the `::`-qualified prefix into `::`, so the wrong-separator id resolves
    the same as the correct one instead of silently failing later. Returns
    `entry` unchanged when it does not match that specific dot-before-last-
    segment shape (no `::` at all, or the remainder after `::` already
    contains its own `::`, or there is no dot to rewrite).
    """
    if "::" not in entry:
        return entry
    path, _, remainder = entry.partition("::")
    if "::" in remainder:
        return entry
    dot_idx = remainder.find(".")
    if dot_idx <= 0:
        return entry
    head, tail = remainder[:dot_idx], remainder[dot_idx + 1 :]
    if not head.isidentifier() or not tail:
        return entry
    return f"{path}::{head}::{tail}"


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

    Also normalizes a dot-separated `Class.method` suffix to the pytest
    `Class::method` form (T-0293) before the schema checks below run, so a
    mis-separated id is fixed at write time instead of landing as evidence
    that can never resolve.
    """
    stripped = normalize_evidence_separator(entry.strip())
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
# frob:ticket T-0398
# frob:doc docs/modules/tickets.md#public-api
def _has_done_report(body: str) -> bool:
    """Whether `body` has a substantive '## Done report' section (D-03):
    thin wrapper kept for call-site stability, delegating to
    `frob.tickets._models.has_substantive_done_report` (the single
    heading-plus-content implementation, dedupe of D-11's twin)."""
    return has_substantive_done_report(body)


def _start_blockers(ticket: Ticket, queue: dict[str, Ticket]) -> list[str]:
    """Blocker ids of `ticket` that are unknown or still in an open state."""
    return [
        b for b in ticket.blocked_by if b not in queue or queue[b].state in _OPEN_STATES
    ]


def _transition_guard(
    ticket: Ticket,
    to: TicketState,
    queue: dict[str, Ticket],
    *,
    covers_scope: bool | None = None,
) -> Result[None, TicketError]:
    """Enforce start-blocker and done-evidence preconditions for `to`."""
    if to == TicketState.IN_PROGRESS:
        open_ids = _start_blockers(ticket, queue)
        if open_ids:
            _log.warning(
                "tickets: %s cannot start, open blockers %s", ticket.id, open_ids
            )
            return Err(TicketError.BlockerOpen)
    if to == TicketState.DONE:
        return _done_transition_guard(ticket, covers_scope=covers_scope)
    return Ok(None)


# T-0215 review round 2: a cmd: entry is only ever valid evidence on a
# docs-kind ticket (COV003 mirrors this at check time). Re-check HERE too,
# not just at add_cmd_evidence write time -- a ticket's kind can be
# hand-edited after evidence was recorded, or a cmd: entry can be
# hand-pasted directly into the ledger, either of which would otherwise
# slip a code-kind ticket through close on unverifiable evidence.
def _done_transition_guard(
    ticket: Ticket, *, covers_scope: bool | None = None
) -> Result[None, TicketError]:
    """Enforce DONE-transition preconditions: evidence + substantive Done
    report present, no cmd: evidence on a kind that disallows it, and (D-02,
    when the caller supplies `covers_scope`) at least one evidence id binds
    to a touched/scope symbol.

    `covers_scope` is injected, never computed here (D-02): answering "does
    an evidence id cover a touched/scope symbol" needs the obligation graph
    (`frob.graph`) and the `TESTS`-edge index `frob.testing`/`frob.gates`
    already build, and `frob.tickets` deliberately stays free of that
    dependency (docs/rework.md cycle-avoidance -- `frob.gates` is the one
    module allowed to join graph + tickets). `covers_scope=None` (the
    default, matching every caller before D-02) skips the check entirely,
    so existing callers/tests are unaffected; a caller with graph access
    (`frob.gates.evidence_covers_scope`, or its own equivalent) opts in by
    passing an explicit `True`/`False`."""
    if not ticket.evidence or not _has_done_report(ticket.body):
        _log.warning(
            "tickets: %s cannot close, missing evidence or a substantive Done report",
            ticket.id,
        )
        return Err(TicketError.MissingEvidence)
    if ticket.kind not in CMD_EVIDENCE_ALLOWED_KINDS and any(
        is_cmd_evidence(e) for e in ticket.evidence
    ):
        _log.warning(
            "tickets: %s is kind=%s but carries cmd: evidence, only "
            "allowed for kind in %s",
            ticket.id,
            ticket.kind,
            sorted(k.value for k in CMD_EVIDENCE_ALLOWED_KINDS),
        )
        return Err(TicketError.EvidenceKindNotAllowed)
    if covers_scope is False:
        _log.warning(
            "tickets: %s cannot close, no evidence id covers a touched/scope symbol",
            ticket.id,
        )
        return Err(TicketError.EvidenceScopeUnbound)
    return Ok(None)


# Blocker resolution needs archived tickets too (a blocker archived after
# `done` must still read as closed, not unknown/open) -- the ticket being
# transitioned itself is always still in the active store (archived
# tickets are done/dropped, terminal, so a lookup that only ever finds one
# there fails the state machine correctly, T-0096).
def _load_ticket_and_queue(
    root: Path, ticket_id: str
) -> Result[tuple[Ticket, dict[str, Ticket]], TicketError]:
    """Load the merged active+archive queue and look up `ticket_id` in it."""
    loaded = _load_merged(root)
    if loaded.is_err:
        return Err(loaded.danger_err)
    queue = loaded.danger_ok
    ticket = queue.get(ticket_id)
    if ticket is None:
        _log.warning("tickets: %s not found under %s", ticket_id, root)
        return Err(TicketError.NotFound)
    return Ok((ticket, queue))


# frob:invariant INV-002
# invariant spec: [INV-002](invariants/INV-002.md)
# frob:doc docs/modules/tickets.md#public-api
def transition(
    root: Path,
    ticket_id: str,
    to: TicketState,
    *,
    covers_scope: bool | None = None,
) -> Result[Ticket, TicketError]:
    """Enforce the state machine; `done` also requires evidence and a
    substantive Done report, and (D-02) an evidence id covering a touched/
    scope symbol whenever the caller supplies `covers_scope=False` (see
    `_done_transition_guard`'s docstring for why this is injected rather
    than computed here)."""
    loaded = _load_ticket_and_queue(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket, queue = loaded.danger_ok

    allowed = _TRANSITIONS.get(ticket.state, frozenset())
    if to not in allowed:
        _log.warning(
            "tickets: %s illegal transition %s -> %s", ticket_id, ticket.state, to
        )
        return Err(TicketError.InvalidTransition)

    guard = _transition_guard(ticket, to, queue, covers_scope=covers_scope)
    if guard.is_err:
        return Err(guard.danger_err)

    updated = ticket.model_copy(update={"state": to})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info("tickets: %s transitioned %s -> %s", ticket_id, ticket.state, to)
    _sync_cross_worktree_lease(root, ticket_id, ticket.state, to, updated.scope)
    return Ok(updated)


# frob:ticket T-0473
def _sync_cross_worktree_lease(
    root: Path,
    ticket_id: str,
    from_state: TicketState,
    to_state: TicketState,
    scope: tuple[str, ...],
) -> None:
    """Keep the cross-worktree lease side-channel (`frob.tickets._leases`,
    T-0473) in sync with every `transition` call: record a lease on entering
    `IN_PROGRESS`, release it on leaving. Best-effort -- `_leases` degrades
    every failure to a logged warning internally, never raising here, so a
    side-channel write failure can never turn a successful ledger
    transition into a reported one."""
    from frob.tickets._leases import record_lease, release_lease

    if to_state is TicketState.IN_PROGRESS:
        record_lease(root, ticket_id, scope)
    elif from_state is TicketState.IN_PROGRESS:
        release_lease(root, ticket_id)


# frob:doc docs/modules/tickets.md#public-api
def add_evidence(
    root: Path,
    ticket_id: str,
    node_ids: Sequence[str],
    collected: frozenset[str] | None = None,
    passed: frozenset[str] | None = None,
) -> Result[Ticket, TicketError]:
    """Validate `node_ids` against `collected` pytest node ids and (D-01)
    against `passed` -- the ids a caller has actually observed PASS on a
    real run -- and append the resolvable, passing ones to the ticket's
    structured evidence list; rejecting the whole batch
    (Err(UnknownEvidence) / Err(EvidenceNotPassing)) if any id fails either
    check, so neither a typo'd id NOR a red/failing test can sneak into
    evidence and surface only at close time (the failure mode this command
    exists to close at write time).

    `collected`/`passed` are supplied by the caller (frob.testing) rather
    than fetched here, keeping this library free of the frob.graph
    dependency frob.testing pulls in. `collected=None` skips resolution
    (schema validation still applies) -- the T-0102 in-process path where
    no collector is available. `passed=None` (default, matching every
    caller before D-01) skips pass-verification the same way -- a caller
    with no test-run oracle available is unaffected; a caller that actually
    ran the tests (`frob.testing.run_selected` or equivalent) opts in by
    passing the observed-passing subset. cmd: evidence entries are exempt
    from `passed` (verified by their own exit-code/digest channel instead,
    see `add_cmd_evidence`/`reverify_cmd_evidence`)."""
    validated = _validate_evidence_list(tuple(node_ids))
    if validated.is_err:
        return Err(validated.danger_err)
    # T-0293: validation normalizes a dot-separated Class.method suffix to
    # the pytest Class::method form -- resolution, pass-checking, and the
    # persisted evidence must all use the NORMALIZED ids from here on, or a
    # dot-form id would still be checked/stored under its original,
    # never-resolving spelling.
    normalized_ids = validated.danger_ok
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    resolution = _check_evidence_resolution(ticket_id, normalized_ids, collected)
    if resolution.is_err:
        return Err(resolution.danger_err)

    passing = _check_evidence_passing(ticket_id, normalized_ids, passed)
    if passing.is_err:
        return Err(passing.danger_err)

    return _append_evidence_and_write(root, ticket, ticket_id, normalized_ids)


def _check_evidence_resolution(
    ticket_id: str, node_ids: Sequence[str], collected: frozenset[str] | None
) -> Result[None, TicketError]:
    """`Err(UnknownEvidence)` if any of `node_ids` fails to resolve against
    `collected`; `collected=None` skips resolution entirely (D-08: this is
    the "unresolved" path -- always logged at WARNING so a `collected=None`
    call is never silent about the gap, even though it cannot reject)."""
    if collected is None:
        _log.warning(
            "tickets: %s evidence %s recorded UNRESOLVED -- no collector "
            "supplied, existence against the current test suite was not "
            "checked (run `frob check` to catch a stale id via COV003)",
            ticket_id,
            list(node_ids),
        )
        return Ok(None)
    unresolved = [nid for nid in node_ids if not matches_collected(nid, collected)]
    if unresolved:
        _log.warning(
            "tickets: %s evidence rejected, unresolved id(s) %s "
            "(the collection cache self-refreshes on the next `frob test` "
            "/ `frob check` run; if it still does not resolve, delete "
            ".frob/pytest-collect.json (or .frob/cargo-collect.json for "
            "rust) to force a rebuild, or fix the id)",
            ticket_id,
            unresolved,
        )
        return Err(TicketError.UnknownEvidence)
    return Ok(None)


def _check_evidence_passing(
    ticket_id: str, node_ids: Sequence[str], passed: frozenset[str] | None
) -> Result[None, TicketError]:
    """`Err(EvidenceNotPassing)` if any non-cmd id in `node_ids` is absent
    from `passed` (D-01); `passed=None` skips the check entirely (no
    pass/fail oracle supplied -- back-compat default, see `add_evidence`)."""
    if passed is None:
        return Ok(None)
    failing = [
        nid for nid in node_ids if not is_cmd_evidence(nid) and nid not in passed
    ]
    if failing:
        _log.warning(
            "tickets: %s evidence rejected, did not pass on last run: %s "
            "(re-run `frob test`, fix the failure, then re-record evidence)",
            ticket_id,
            failing,
        )
        return Err(TicketError.EvidenceNotPassing)
    return Ok(None)


def _append_evidence_and_write(
    root: Path, ticket: Ticket, ticket_id: str, node_ids: Sequence[str]
) -> Result[Ticket, TicketError]:
    """Merge new `node_ids` into `ticket.evidence` (deduplicated) and write
    the updated ticket."""
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
# frob:tests tests/test_tickets_cmd_evidence.py::TestCmdEvidence.test_exit_zero
# frob:tests tests/test_tickets_cmd_evidence.py::TestCmdEvidence.test_nonzero_exit
def run_cmd_evidence(command: str) -> Result[str, TicketError]:
    """Run `command` through the shell and fold its outcome into one evidence
    string (`cmd:<command> exit=0 sha256=<12-hex>`) -- the non-pytest
    evidence primitive `add_cmd_evidence` records for docs/design tickets
    (T-0215). A nonzero exit or a command that fails to launch at all is
    Err(EvidenceCmdFailed): a broken or never-run command can never
    masquerade as evidence just by being named. The digest is taken over
    stdout only (deterministic across whitespace-only stderr noise) so the
    same command run twice against the same repo state records the same
    entry instead of appending a new one every time.
    """
    completed = _run_evidence_command(command)
    if completed.is_err:
        return Err(completed.danger_err)
    digest = hashlib.sha256(completed.danger_ok.stdout.encode("utf-8")).hexdigest()[:12]
    entry = f"cmd:{command} exit=0 sha256={digest}"
    return validate_evidence(entry)


_CMD_EVIDENCE_PARSE_RE = re.compile(
    r"^cmd:(?P<command>.+) exit=0 sha256=(?P<sha>[0-9a-f]{12})$"
)


# frob:ticket T-0398
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_evidence_integrity.py::TestD10CmdEvidenceReverify.test_reverify_true_when_command_still_reproduces  # noqa: E501
def reverify_cmd_evidence(entry: str) -> Result[bool, TicketError]:
    """Re-run the command a `cmd:` evidence entry recorded and confirm it
    still exits 0 with the SAME stdout digest (D-10): `run_cmd_evidence`'s
    sha256 is otherwise a record-time-only attestation nothing ever
    re-checks. `Ok(True)`/`Ok(False)` report whether the command still
    reproduces; `Err(MalformedEvidence)` if `entry` is not a well-formed
    `cmd:` entry at all.

    Deliberately opt-in, not wired into `_done_transition_guard`/COV003 by
    default: re-running an arbitrary recorded command on every check is
    exactly the cost/non-idempotence tradeoff `_evidence_valid_for_ticket`
    already documents choosing NOT to pay unconditionally (a docs command
    may be slow, or legitimately non-deterministic in a way that does not
    indicate the underlying claim is false). A caller that wants the
    stronger guarantee for a specific entry calls this directly."""
    match = _CMD_EVIDENCE_PARSE_RE.match(entry)
    if match is None:
        _log.warning("tickets: reverify_cmd_evidence: not a cmd: entry: %r", entry)
        return Err(TicketError.MalformedEvidence)
    command, recorded_sha = match.group("command"), match.group("sha")
    completed = _run_evidence_command(command)
    if completed.is_err:
        _log.warning("tickets: reverify_cmd_evidence: %r no longer exits 0", command)
        return Ok(False)
    digest = hashlib.sha256(completed.danger_ok.stdout.encode("utf-8")).hexdigest()[:12]
    matches = digest == recorded_sha
    if not matches:
        _log.warning(
            "tickets: reverify_cmd_evidence: %r stdout digest changed (%s -> %s)",
            command,
            recorded_sha,
            digest,
        )
    return Ok(matches)


def _run_evidence_command(
    command: str,
) -> Result[subprocess.CompletedProcess, TicketError]:
    """Spawn `command` through the shell; `Err(EvidenceCmdFailed)` if it
    fails to launch or exits nonzero."""
    try:
        completed = subprocess.run(
            command,
            shell=True,  # noqa: S602 -- caller-supplied vetted command, T-0215
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        _log.error("tickets: evidence command %r failed to launch: %s", command, exc)
        return Err(TicketError.EvidenceCmdFailed)
    if completed.returncode != 0:
        _log.warning(
            "tickets: evidence command %r exited %d (stderr tail: %r)",
            command,
            completed.returncode,
            completed.stderr[-500:],
        )
        return Err(TicketError.EvidenceCmdFailed)
    return Ok(completed)


def _check_cmd_evidence_kind(
    ticket_id: str, kind: TicketKind
) -> Result[None, TicketError]:
    """`Err(EvidenceKindNotAllowed)` unless `kind` is in
    `CMD_EVIDENCE_ALLOWED_KINDS`."""
    if kind not in CMD_EVIDENCE_ALLOWED_KINDS:
        _log.warning(
            "tickets: %s is kind=%s, cmd evidence only allowed for kind in %s",
            ticket_id,
            kind,
            sorted(k.value for k in CMD_EVIDENCE_ALLOWED_KINDS),
        )
        return Err(TicketError.EvidenceKindNotAllowed)
    return Ok(None)


# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_cmd_evidence.py::TestKindGate.test_docs_kind_closes
# frob:tests tests/test_tickets_cmd_evidence.py::TestKindGate.test_bug_kind_rejected
def add_cmd_evidence(
    root: Path, ticket_id: str, command: str
) -> Result[Ticket, TicketError]:
    """Kind-gated non-pytest evidence channel (T-0215): runs `command` via
    `run_cmd_evidence` and appends the resulting entry to `ticket_id`'s
    structured evidence list. Only tickets whose `kind` is in
    `CMD_EVIDENCE_ALLOWED_KINDS` (currently just `docs`) may use this --
    code-kind tickets (bug/feature/security/ux/invariant/incident) always
    still require real pytest node ids via `add_evidence`, enforced here
    with Err(EvidenceKindNotAllowed) so a code change can never close on an
    unrelated shell command's exit status alone.
    """
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    kind_check = _check_cmd_evidence_kind(ticket_id, ticket.kind)
    if kind_check.is_err:
        return Err(kind_check.danger_err)

    recorded = run_cmd_evidence(command)
    if recorded.is_err:
        return Err(recorded.danger_err)
    entry = recorded.danger_ok

    merged = ticket.evidence if entry in ticket.evidence else ticket.evidence + (entry,)
    updated = ticket.model_copy(update={"evidence": merged})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info("tickets: %s recorded cmd evidence (%s)", ticket_id, entry)
    return Ok(updated)


# frob:ticket T-0458
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestRenderEvidenceBlock.test_mixed_cmd_and_pytest_ids  # noqa: E501
def render_evidence_block(evidence: Sequence[str]) -> str:
    """Auto-fill a Done report's Evidence section from a ticket's already-
    recorded evidence ids alone (T-0458 REFINEMENT).

    No fresh collection or test run is needed here: every id in `evidence`
    was ALREADY validated resolvable-and-passing (pytest, `add_evidence`'s
    D-01 `passed` check) or exit=0 (`cmd:` entries, `add_cmd_evidence`) at
    the moment it was accepted into the ticket -- so this just renders what
    frob already knows to be true, instead of the agent retyping node ids
    and pass counts by hand (the class of drift that produced this
    session's stale-evidence-id incidents).
    """
    if not evidence:
        return "(no evidence recorded)"
    lines = []
    for eid in evidence:
        if is_cmd_evidence(eid):
            lines.append(f"- `{eid}` (cmd evidence, exit=0)")
        else:
            lines.append(f"- `{eid}` (pytest node id, verified passing when recorded)")
    return "\n".join(lines)


# frob:ticket T-0458
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestComputeChangedLines.test_non_git_root_returns_empty  # noqa: E501
def compute_changed_lines(root: Path, base_ref: str = "main") -> tuple[str, ...]:
    """Best-effort `git diff --stat <base_ref>...HEAD` lines for a Done
    report's Changed section (T-0458 REFINEMENT) -- pulled straight from
    git, never retyped by the agent (the exact class of error that dropped
    `render.md` / mis-listed files by hand this session).

    Returns an empty tuple (never raises, never Err) if `root` is not a git
    checkout or the diff itself fails -- the Changed block is auxiliary
    evidence for the report, not a precondition for writing one; a caller
    that wants a hard failure on a broken git state should check `root`
    itself before calling `set_done_report`.
    """
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "diff", "--stat", f"{base_ref}...HEAD"])
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        _log.warning(
            "tickets: git diff --stat %s...HEAD unavailable for done-report "
            "Changed block (root=%s)",
            base_ref,
            root,
        )
        return ()
    return tuple(line for line in spawned.danger_ok.stdout.splitlines() if line.strip())


# frob:ticket T-0458
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestRenderChangedBlock.test_lines_rendered_fenced  # noqa: E501
def render_changed_block(lines: Sequence[str]) -> str:
    """Render `compute_changed_lines`'s output as a Done report Changed
    section (fenced verbatim, since git's `--stat` output is already
    human-readable columns) (T-0458)."""
    if not lines:
        return "(no changed files detected)"
    return "```\n" + "\n".join(lines) + "\n```"


# frob:ticket T-0458
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_composes_all_three_sections  # noqa: E501
def compose_done_report(
    why: str, changed_lines: Sequence[str], evidence: Sequence[str]
) -> str:
    """Compose a full '## Done report' section: the caller's narrative
    `why` plus AUTO-FILLED Changed (`render_changed_block`) and Evidence
    (`render_evidence_block`) sections (T-0458 REFINEMENT) -- the mechanical
    parts are always generated, never hand-typed, so they can never drift
    from what frob and git actually recorded."""
    why_text = why.strip() or "(no narrative supplied)"
    changed_block = render_changed_block(changed_lines)
    evidence_block = render_evidence_block(evidence)
    return (
        f"{DONE_REPORT_HEADING}\n\n"
        f"{why_text}\n\n"
        f"### Changed\n{changed_block}\n\n"
        f"### Evidence\n{evidence_block}\n"
    )


# frob:ticket T-0458
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_composes_and_writes_atomically  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_caller_never_touches_markdown  # noqa: E501
def set_done_report(
    root: Path, ticket_id: str, *, why: str, base_ref: str = "main"
) -> Result[Ticket, TicketError]:
    """THE single write path for a ticket's Done report (T-0458): compose
    `why` (the caller's narrative -- the ONLY thing the caller supplies)
    with auto-filled Changed (`compute_changed_lines` vs `base_ref`) and
    Evidence (`render_evidence_block`, from the ticket's own recorded
    evidence) sections, then splice the result into `body`'s '## Done
    report' section via `replace_done_report_section` -- the caller never
    parses or edits markdown directly, and never re-derives block
    boundaries by hand (the exact failure mode -- a dropped marker, a
    mis-listed Changed/Evidence block, an Edit landing mid-section -- that
    repeatedly corrupted `tickets.md` when done by hand).

    Held under `ledger_lock` end to end (load, compose, write) so a
    concurrent `set_done_report`/`add_evidence`/`new_ticket` call on the
    same ledger can never interleave with this one (T-0458 single-writer
    invariant)."""
    with ledger_lock(root):
        loaded = _load_one(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket = loaded.danger_ok
        changed_lines = compute_changed_lines(root, base_ref)
        report = compose_done_report(why, changed_lines, ticket.evidence)
        updated = ticket.model_copy(
            update={"body": replace_done_report_section(ticket.body, report)}
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s Done report set (%d evidence id(s), %d changed line(s))",
        ticket_id,
        len(ticket.evidence),
        len(changed_lines),
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
    "ScopeChangeEntry",
    "ScopeChangeOp",
    "Ticket",
    "TicketError",
    "TicketKind",
    "TicketQueue",
    "TicketSpec",
    "TicketState",
    "add_cmd_evidence",
    "add_evidence",
    "archive",
    "attach",
    "clipboard_has_image",
    "compose_done_report",
    "compute_changed_lines",
    "doable",
    "doable_blocked",
    "is_cmd_evidence",
    "land",
    "large_glob_warnings",
    "leased_by",
    "ledger_lock",
    "load_active",
    "load_queue",
    "mutate_scope",
    "Stride",
    "migrate",
    "new_ticket",
    "renumber",
    "record_failure",
    "render_changed_block",
    "render_evidence_block",
    "reverify_cmd_evidence",
    "run_cmd_evidence",
    "scope_breadth_context",
    "scope_matches",
    "scope_overlap_globs",
    "set_done_report",
    "splice_ledger",
    "transition",
    "validate_evidence",
]

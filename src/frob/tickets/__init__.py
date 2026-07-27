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
import shlex
import subprocess
import tomllib
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.excludes import is_test_file
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.tickets._land import land, splice_ledger
from frob.tickets._leases import (
    LeaseError,
    is_lease_ttl_expired,
    lease_age_seconds,
    leases_dir,
    read_all_leases,
    resolve_lease,
    sweep_worktrees,
)
from frob.tickets._live_tracker import live_tracker_citations
from frob.tickets._models import (
    BOARD_STATES,
    CMD_EVIDENCE_ALLOWED_KINDS,
    DONE_REPORT_HEADING,
    DROP_REASON_HEADING,
    FAILURE_LOG_HEADING,
    LEDGER_PATH,
    OVER_BROAD_LITERAL_GLOBS,
    PRIORITY_RANK,
    AcceptanceCriterion,
    Attachment,
    AttachmentSource,
    BoardColumn,
    DoneReportClaims,
    EpicRollup,
    FailureEntry,
    LandError,
    LandReport,
    Origin,
    Priority,
    RenumberReport,
    ReviewEntry,
    ReviewVerdict,
    ScopeChangeEntry,
    ScopeChangeOp,
    SprintReport,
    Stride,
    Ticket,
    TicketError,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
    TicketTier,
    _done_report_section_lines,
    _glob_is_subset,
    has_substantive_done_report,
    is_cmd_evidence,
    matches_collected,
    parse_claims_from_done_report,
    render_claims_block,
    replace_done_report_section,
    scope_matches,
    scope_overlap_globs,
    unbound_acceptance,
)
from frob.tickets._models import _split_scope_entries as _normalize_scope_entries
from frob.tickets._mutation_evidence import (
    ConfirmatoryFinding,
    MutationEvidenceError,
    check_ticket_mutation_evidence,
)
from frob.tickets._new_gate_rule_acceptance import (
    missing_acceptance_for_new_rules,
    new_gate_rule_ids,
)
from frob.tickets._provisional import is_draft_id, mint_draft_id, on_default_branch
from frob.tickets._reconcile import ReconcileReport, reconcile
from frob.tickets._store import (
    archive_path,
    atomic_write,
    attachments_dir,
    ledger_digest,
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
from frob.tickets._worktree_guard import agent_env_exports, enforce_worktree_lease
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

# frob:ticket T-0579
# `frob ticket drop` writes its dated reason line under this heading instead
# of the hand-edited freeform prose the pre-T-0579 workflow used.
#
# T-0848: these are `frob.tickets._models`'s own `FAILURE_LOG_HEADING` /
# `DROP_REASON_HEADING` re-exported under this module's private naming
# convention, not a second hand-typed copy -- `_models._done_report_
# section_end`'s structural-sentinel set must never drift out of sync with
# the headings this module actually writes.
_FAILURE_LOG_HEADING = FAILURE_LOG_HEADING
_DROP_REASON_HEADING = DROP_REASON_HEADING


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
# frob:ticket T-0633
# frob:ticket T-0764
# frob:ticket T-0843
# frob:ticket T-0889
# frob:tests tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_archive  # noqa: E501
# frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_refuses_when_a_live_lease_exists  # noqa: E501
# frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_force_overrides_the_live_lease_refusal  # noqa: E501
# frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_ignores_a_stale_lease_from_a_removed_worktree  # noqa: E501
# frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_ignores_a_live_lease_for_a_ticket_it_would_not_touch  # noqa: E501
# frob:waive TEST005 reason="archive 75.0% branch cover, debt T-0160"
# T-0633: the whole load-filter-write sequence below is held under ONE
# `ledger_lock` span, not just the final `write_all`/`write_archive` calls
# individually -- `load_all` used to run UNLOCKED, so a concurrent
# single-ticket write (`new_ticket`, `transition`, ...) landing in the
# window between this function's unlocked read and its later locked
# `write_all(keep)` was silently reverted: `keep` was computed from the
# stale pre-lock snapshot and `write_all` replaces the ENTIRE active
# ledger with it, bytes and all, clobbering whatever the concurrent writer
# had just spliced in. Holding the lock across the full sequence
# (reentrant per thread, see `ledger_lock`'s docstring) makes the read and
# the write one atomic unit, so no writer's splice can ever land in the
# gap and then get overwritten.
#
# T-0764: `ledger_lock` only ever serializes writers against THIS repo's
# lock file -- it says nothing about a worktree that is mid-`start`
# (evidence/acceptance already recorded locally, not yet landed) whose
# OWN change never runs through this process at all. Archiving in that
# window is exactly the T-0753 field incident: the archiving worktree's
# rewritten `tickets.md` becomes the new `main`, and the in-flight
# worktree's later section 10b restore (`git checkout main --
# tickets.md`) silently reverts its own start/evidence/acceptance back to
# `queued`. `archive` refuses (`Err(ArchiveLiveLeaseExists)`) unless
# `force=True` -- archiving is meant to run in a quiet window (the TICK003
# remediation text already says so; this makes it enforced, not just
# advised). A lease for a worktree that no longer exists on disk is
# stale, not live (`read_all_leases` already filters those out), so a
# crashed/abandoned worktree can never wedge archive forever.
#
# T-0843: the guard used to refuse whenever ANY live lease existed
# anywhere in the repo, even one for a ticket archive would never touch --
# in-progress tickets are never archived (only DONE/DROPPED tickets are),
# so a lease for an in-progress ticket poses no T-0753 risk to that
# ticket's own block. Narrowed (`_refuse_archive_if_leased`) to refuse
# only when a live lease's ticket_id is actually among the tickets this
# call would move into `tickets-archive.md` (e.g. a DONE/DROPPED ticket
# whose lease was never released) -- a red TICK003 caused by unrelated
# in-flight work no longer has to wait for that work to finish.
# frob:waive AFFECT001 reason="T-0976 pure internal refactor: extraction of _refuse_archive_if_leased from this already-documented function, no external contract/behavior change, doc anchor(s) remain accurate as-is"  # noqa: E501
def archive(root: Path, *, force: bool = False) -> Result[int, TicketError]:
    """Move every done/dropped ticket from the active store into
    tickets-archive.md, verbatim (same section format, still tracked and
    greppable); the active ledger keeps only open work. Idempotent -- a
    second call with nothing newly done/dropped moves nothing and returns
    Ok(0). Returns the number of tickets moved. See the comment block
    directly above this function for the full T-0633/T-0764/T-0843
    locking and live-lease-refusal rationale."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        active_digest = ledger_digest(ledger_path(root))
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

        if not force:
            guard = _refuse_archive_if_leased(root, to_archive)
            if guard.is_err:
                return Err(guard.danger_err)

        return _write_archived_and_active(root, active, to_archive, active_digest)


# frob:ticket T-0976
def _refuse_archive_if_leased(
    root: Path, to_archive: dict
) -> Result[None, TicketError]:
    """`archive`'s T-0843 live-lease guard: `Err(ArchiveLiveLeaseExists)` if
    any ticket in `to_archive` still holds a live cross-worktree lease
    (T-0753's field-incident risk), else `Ok(None)` -- split from
    `archive`'s own lock-held body."""
    live_leases = read_all_leases(root)
    leased_to_archive = sorted(
        lease.ticket_id for lease in live_leases if lease.ticket_id in to_archive
    )
    if not leased_to_archive:
        return Ok(None)
    _log.error(
        "tickets: archive refused -- %d ticket(s) this call "
        "would move into tickets-archive.md still hold a live "
        "cross-worktree lease (%s); archiving now would risk "
        "reverting their start/evidence/acceptance on next "
        "restore (T-0753) -- run in a quiet window or pass "
        "--force",
        len(leased_to_archive),
        ", ".join(leased_to_archive),
    )
    return Err(TicketError.ArchiveLiveLeaseExists)


# frob:ticket T-0889
def _write_archived_and_active(
    root: Path,
    active: dict[str, Ticket],
    to_archive: dict[str, Ticket],
    active_digest: str | None,
) -> Result[int, TicketError]:
    """Merge `to_archive` into the archive file and drop it from the active
    ledger, in that order; `Err(DuplicateId)` on an id already archived.

    `active_digest` (T-0889) is the `ledger_digest` snapshot `archive`'s
    caller took of the active ledger immediately before its `load_all` --
    passed through to `write_all` as `expected_digest` so the wholesale
    active rewrite refuses rather than clobbers if anything touched
    tickets.md since that load (still inside the one `ledger_lock` span
    `archive` holds end to end, so this is defense in depth against an
    external replacement racing the lock, not a substitute for it)."""
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
    active_write = write_all(root, keep, expected_digest=active_digest)
    if active_write.is_err:
        return Err(active_write.danger_err)

    _log.info("tickets: archived %d ticket(s)", len(to_archive))
    return Ok(len(to_archive))


# frob:ticket T-0162
# frob:doc docs/modules/tickets.md#decision-record-t-0162
# frob:waive COV007 reason="the decision-record anchor documents THIS \
# private function's own allocation algorithm/design rationale (why \
# provisional ids vs branch-tip scanning vs content-nonce were compared, \
# T-0162), not the public API surface -- the private symbol genuinely is \
# the documented contract here, not a caller-side summary"
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
        priority=spec.priority,
        blocked_by=spec.blocked_by,
        parent=spec.parent,
        tier=spec.tier,
        sprint=spec.sprint,
        scope=spec.scope,
        evidence=evidence,
        attachments=(),
        acceptance=spec.acceptance,
        threat=spec.threat,
        component=spec.component,
        labels=spec.labels,
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
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
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
# frob:ticket T-0633
# frob:ticket T-0889
# frob:tests tests/test_tickets_ledger_concurrency.py::TestLedgerLockSpansWholesaleOperations.test_concurrent_ledger_lock_acquisition_serializes  # noqa: E501
# frob:waive TEST005 reason="renumber 69.2% branch cover, debt T-0160"
def renumber(root: Path) -> Result[int, TicketError]:
    """Reassign ticket ids to a contiguous T-0001.. sequence (ordered by
    current id), rewriting blocked_by/parent references so the queue stays
    consistent. The remedy for sequential-id collisions after a worktree
    merge (T-0012). Returns the number of tickets renumbered.

    T-0633: `load_all` and the eventual `write_all` are now held under one
    `ledger_lock` span (same fix and rationale as `archive`'s docstring) --
    previously the load ran unlocked, so a concurrent single-ticket write
    landing before this function's own locked `write_all` was silently
    reverted by the stale wholesale rewrite.
    """
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        digest = ledger_digest(ledger_path(root))
        loaded = load_all(root)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ordered = sorted(loaded.danger_ok.values(), key=lambda t: t.id)
        mapping = {t.id: f"T-{i + 1:04d}" for i, t in enumerate(ordered)}
        if _is_contiguous(ordered, mapping):
            _log.info("tickets: renumber -- already contiguous, nothing to do")
            return Ok(0)
        new_map, renumbered = _apply_renumber(ordered, mapping)
        result = write_all(root, new_map, expected_digest=digest)
        if result.is_err:
            return Err(result.danger_err)
    _log.info("tickets: renumbered %d ticket(s)", renumbered)
    return Ok(renumbered)


_DIRECTIVE_LINE_RE = re.compile(r"frob:(ticket|waive|todo|tests|invariant|doc)\b")

# T-0577: registry disposition targets (docs/design/registry/*.yaml's
# `disposition: "deferred:<ticket>"` / `"duplicate_of:<ticket>"` values, per
# `frob.registry._models.parse_disposition`'s grammar) are ticket-id
# REFERENCES exactly like a `frob:ticket` directive line, but they live in
# YAML data files, not source comments -- `_DIRECTIVE_LINE_RE` never matched
# them. A draft id finalized at land time used to leave every registry
# yaml's `deferred:T-draft-...` pointing at a now-dead id, silently
# breaking REG003 (deferred-to-missing-ticket) until a human hand-swapped it
# (the real T-0388/compliance.yaml incident this pattern closes). Matched
# independent of `_DIRECTIVE_LINE_RE` so a bare `disposition:
# "deferred:T-draft-xxxx"` line (no `frob:` prefix at all) still rewrites.
_REGISTRY_REF_RE = re.compile(r"(?:deferred|duplicate[_-]of):\S+")


def _rewrite_registry_references(
    text: str, old_id: str, new_id: str
) -> tuple[str, int]:
    """Replace whole-word `old_id` with `new_id` wherever it appears as the
    target of a `deferred:`/`duplicate_of:` registry disposition (T-0577,
    see `_REGISTRY_REF_RE`'s doc) -- never elsewhere, so a ticket id
    mentioned only in registry prose/free text is left alone."""
    id_re = re.compile(rf"\b{re.escape(old_id)}\b")
    hits = 0

    def _sub_ref(match: re.Match[str]) -> str:
        nonlocal hits
        rewritten, n = id_re.subn(new_id, match.group(0))
        hits += n
        return rewritten

    return _REGISTRY_REF_RE.sub(_sub_ref, text), hits


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
    """Every tracked non-ledger file whose directive lines OR registry
    disposition targets (`_rewrite_registry_references`, T-0577) mention
    `old_id`, mapped to its rewritten text and the number of references
    replaced (both classes combined)."""
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
        directive_text, directive_hits = _rewrite_directive_references(
            text, old_id, new_id
        )
        rewritten, registry_hits = _rewrite_registry_references(
            directive_text, old_id, new_id
        )
        hits = directive_hits + registry_hits
        if hits:
            changed[path] = (rewritten, hits)
    return changed


# frob:ticket T-0889
def _load_and_validate_renumber_ids(
    root: Path, old_id: str, new_id: str
) -> Result[
    tuple[dict[str, Ticket], dict[str, Ticket], str | None, str | None], TicketError
]:
    """Load the active+archive ledgers and validate `old_id`/`new_id` are
    renumber-able: not equal, `old_id` present, `new_id` free.

    Also returns each ledger's `ledger_digest` snapshot at load time
    (T-0889), so `_persist_renumber`'s eventual wholesale `write_all`/
    `write_archive` can refuse instead of clobbering if either file changed
    on disk since this load."""
    if old_id == new_id:
        _log.warning("tickets: renumber_one %s -> %s is a no-op id", old_id, new_id)
        return Err(TicketError.InvalidTransition)

    active_digest = ledger_digest(ledger_path(root))
    active_loaded = load_all(root)
    if active_loaded.is_err:
        return Err(active_loaded.danger_err)
    archive_digest = ledger_digest(archive_path(root))
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
    return Ok((active_map, archive_map, active_digest, archive_digest))


# frob:ticket T-0889
def _persist_renumber(
    root: Path,
    *,
    new_active_map: dict[str, Ticket],
    active_changed: int,
    new_archive_map: dict[str, Ticket],
    archive_changed: int,
    code_changes: dict[Path, tuple[str, int]],
    active_digest: str | None = None,
    archive_digest: str | None = None,
) -> Result[None, TicketError]:
    """Write back the renumbered active/archive ledgers (if changed) and
    every rewritten code-reference file.

    `active_digest`/`archive_digest` (T-0889) are the `ledger_digest`
    snapshots `_load_and_validate_renumber_ids` took at load time, threaded
    through to `write_all`/`write_archive` as `expected_digest` so a
    wholesale rewrite refuses rather than clobbers if either ledger changed
    on disk since that load."""
    if active_changed:
        write_result = write_all(root, new_active_map, expected_digest=active_digest)
        if write_result.is_err:
            return Err(write_result.danger_err)
    if archive_changed:
        archive_write = write_archive(
            root, new_archive_map, expected_digest=archive_digest
        )
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
# frob:ticket T-0633
# frob:ticket T-0889
# frob:tests tests/test_tickets_ledger_concurrency.py::TestRenumberOneRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_renumber_one  # noqa: E501
# frob:waive TEST005 reason="renumber_one 68.3% branch cover, debt T-0160"
def renumber_one(
    root: Path, old_id: str, new_id: str, *, dry_run: bool = False
) -> Result[RenumberReport, TicketError]:
    """Atomically rewrite ONE ticket's id everywhere: its ledger section
    (active or archive, id + every blocked_by/parent reference across BOTH
    stores) and every `frob:ticket`/`frob:waive`/`frob:todo`/`frob:tests`/
    `frob:invariant`/`frob:doc` directive line across the tracked tree that
    names it.

    T-0633: the load (`_load_and_validate_renumber_ids`) and the eventual
    persist (`_persist_renumber`, which calls `write_all`/`write_archive`)
    are held under one `ledger_lock` span for a non-dry-run call -- this is
    `finalize_draft`'s rename primitive (T-0162), so the same TOCTOU that
    `archive`/`renumber` had (an unlocked load, then a locked wholesale
    write built from that stale snapshot silently reverting a concurrent
    single-ticket write in between) applied here too, and matters more:
    `finalize_draft` runs at `frob ticket land` time, exactly when a
    concurrent worktree's ledger write is most likely to be in flight."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_and_validate_renumber_ids(root, old_id, new_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        active_map, archive_map, active_digest, archive_digest = loaded.danger_ok
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
            active_digest=active_digest,
            archive_digest=archive_digest,
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


# frob:invariant INV-032
# frob:ticket T-0715
def _doable_candidates(queue: TicketQueue) -> list[Ticket]:
    """Queued/planned LEAF tickets (tier=TICKET) that currently have no open
    blockers, unordered. T-0715: an EPIC/STORY never surfaces here even if
    it has no `blocked_by` of its own -- only a leaf ticket is ever
    dispatchable work; an epic/story is pure organization, not a unit an
    agent starts directly."""
    return [
        t
        for t in queue.tickets.values()
        if t.state in (TicketState.QUEUED, TicketState.PLANNED)
        and t.tier is TicketTier.TICKET
        and not _open_blockers(queue, t)
    ]


# frob:ticket T-0453
# T-0524: frob:doc removed -- this feeds `leased_by` (public), which
# already carries the same docs/modules/tickets.md#public-api anchor
# (COV007: a private helper does not need its own copy).
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
# T-0524: frob:doc removed -- feeds `scope_breadth_context` (public),
# which already carries the same docs/modules/tickets.md#public-api
# anchor (COV007).
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


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_defaults_false_with_no_frob_toml  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_true_when_configured  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestLoadRequireReviewForClose.test_false_when_absent_from_section  # noqa: E501
def load_require_review_for_close(root: Path) -> bool:
    """Read `[tickets] require_review_for_close` from `frob.toml` (T-0571):
    the strict-mode gate that requires `close` to see at least one
    `verdict: approve` review record naming the current commit. Absent
    config, an unreadable/malformed file, or a non-bool value all default to
    `False` -- off by default for backward compat, matching every other
    optional `[tickets]` toggle here (`_load_large_glob_max_files`)."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return False
    try:
        with toml_path.open("rb") as handle:
            doc = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning("tickets: could not parse %s: %s", toml_path, exc)
        return False
    value = doc.get("tickets", {}).get("require_review_for_close")
    return value is True


# frob:ticket T-0453
# T-0524: frob:doc removed -- feeds `_repo_files`/`scope_breadth_context`
# (public), which already carries the same
# docs/modules/tickets.md#public-api anchor (COV007).
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
# T-0524: frob:doc removed -- feeds `_repo_files`/`scope_breadth_context`
# (public), which already carries the same
# docs/modules/tickets.md#public-api anchor (COV007).
def _repo_files_git(root: Path) -> tuple[str, ...] | None:
    """`git ls-files` under `root` -- tracked files only, `root`-relative
    posix paths, breadth-excluded paths dropped -- or `None` if `root` is
    not a git work tree / `git` is unavailable (T-0453 perf fix: this
    replaces a full-tree `rglob` walk, which used to include the ~129
    stale worktrees under `.claude/worktrees/` and made `frob ticket
    doable` take minutes).

    T-0803: routed through `frob.gitio.run_argv` (gains `guarded_subprocess_
    run`'s `FROB_DISABLE_EXEC` kill switch transitively, T-0778) instead of
    a bare `subprocess.run` -- this was the one remaining git spawn in the
    package bypassing the guard."""
    from frob.gitio import run_argv

    spawned = run_argv(["git", "-C", str(root), "ls-files"], timeout_s=10)
    if spawned.is_err:
        _log.warning("tickets: git ls-files failed under %s", root)
        return None
    result = spawned.danger_ok
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
# T-0524: frob:doc removed -- feeds `_repo_files`/`scope_breadth_context`
# (public), which already carries the same
# docs/modules/tickets.md#public-api anchor (COV007).
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
# T-0524: frob:doc removed -- feeds `scope_breadth_context` (public),
# which already carries the same docs/modules/tickets.md#public-api
# anchor (COV007).
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
# T-0524: frob:doc removed -- feeds `_over_broad_scope_entries`, whose own
# caller `leased_by` (public) already carries the same
# docs/modules/tickets.md#public-api anchor (COV007).
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
# T-0524: frob:doc removed -- called from `leased_by` (public), which
# already carries the same docs/modules/tickets.md#public-api anchor
# (COV007).
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
    all_leases: tuple[tuple[str, tuple[str, ...]], ...] | None = None,
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

    Likewise, pass a precomputed `all_leases` (`_all_leases(queue, root)`)
    when calling this per-candidate in a loop (`doable`/`doable_blocked`
    do) so the local-ledger-union-with-cross-worktree-leases computation
    runs ONCE for the whole call, not once per candidate (T-0773 perf fix
    -- `frob.tickets._leases.read_all_leases` is itself memoized per
    process now, so this second layer of threading is belt-and-suspenders
    rather than the only fix, but it matches the existing `breadth`
    pattern and avoids even the memoized read's dict-lookup/tuple-copy
    overhead per candidate). Omitting it computes it internally, same
    default-to-internal convention as `breadth`.
    """
    if root is not None and breadth is None:
        breadth = scope_breadth_context(root)
    if all_leases is None:
        all_leases = _all_leases(queue, root)
    hits: list[tuple[str, str]] = []
    for holder_id, holder_scope in all_leases:
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


# frob:ticket T-0716
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease_overlay.py::TestDisplayState.test_queued_with_live_lease_decorated  # noqa: E501
# frob:tests tests/test_tickets_lease_overlay.py::TestDisplayState.test_queued_with_stale_lease_undecorated  # noqa: E501
# frob:tests tests/test_tickets_lease_overlay.py::TestDisplayState.test_ledger_in_progress_undecorated  # noqa: E501
# frob:tests tests/test_tickets_lease_overlay.py::TestDisplayState.test_no_root_never_decorates  # noqa: E501
def display_state(ticket: Ticket, root: Path | None) -> str:
    """`ticket`'s display state for `frob ticket list`/`show` (T-0716): the
    ledger `state.value`, OVERLAID (never written back to the ledger --
    writing a worktree's view into main's ledger is exactly the
    corruption class T-0633/T-0682 fixed) with `@<worktree-basename>` when
    the ledger still shows `ticket` QUEUED/PLANNED but a live cross-worktree
    lease for it exists (`read_all_leases`, which already drops leases
    whose worktree path no longer exists -- T-0473/T-0476 stale-lease
    handling reused here verbatim, not re-implemented).

    A ledger-recorded `IN_PROGRESS` ticket is returned undecorated (plain
    `"in-progress"`) -- that state is already visible without a lease, and
    the `@worktree` marker exists specifically to surface the OTHER case:
    a ticket a worktree has started that main's own ledger hasn't learned
    about yet. `root=None` (no repo to consult the shared lease directory
    from) always returns the plain ledger state, matching `leased_by`'s
    own `root=None` degrade-quietly convention."""
    if root is not None and ticket.state in (TicketState.QUEUED, TicketState.PLANNED):
        for lease in read_all_leases(root):
            if lease.ticket_id == ticket.id:
                worktree_name = Path(lease.worktree).name
                return f"in-progress@{worktree_name}"
    return ticket.state.value


# frob:ticket T-0752
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_dispatch_stale.py::TestHasLiveLease.test_queued_with_live_lease_is_in_flight  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestHasLiveLease.test_queued_with_no_lease_is_not_in_flight  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestHasLiveLease.test_no_root_never_in_flight  # noqa: E501
def has_live_lease(ticket: Ticket, root: Path | None) -> bool:
    """Whether `ticket` itself (not a scope collision with some OTHER
    ticket -- that is `leased_by`'s job) currently has a live lease against
    it, per the same `display_state`/`read_all_leases` overlay `frob ticket
    list` already uses (T-0716) -- reused verbatim here rather than
    re-reading the lease directory a second way. Powers `doable`'s
    in-flight/dispatchable row split (T-0752): a row this returns `True`
    for is being worked by SOME worktree already, even though the local
    ledger may still show it `queued`/`planned`, so it belongs in the
    IN-FLIGHT section, not the "next thing to dispatch" one."""
    return display_state(ticket, root) != ticket.state.value


#: Default per-priority staleness threshold (hours) past which a
#: dispatchable (unleased, unblocked) CRITICAL/HIGH ticket is considered
#: dangerously undispatched (T-0752, user mandate: T-0731 sat
#: filed-but-undispatched for hours). Only CRITICAL/HIGH carry a default --
#: MEDIUM/LOW are not alarmed on by default (a queue always has some).
_DISPATCH_STALE_DEFAULT_HOURS: dict[Priority, float] = {
    Priority.CRITICAL: 4.0,
    Priority.HIGH: 24.0,
}


# frob:ticket T-0752
def _dispatch_stale_thresholds(root: Path) -> dict[Priority, float]:
    """Per-priority undispatched-staleness thresholds, in hours (T-0752),
    from `frob.toml`'s `[tickets]` table (`dispatch_stale_critical_hours`/
    `dispatch_stale_high_hours`), defaulting to
    `_DISPATCH_STALE_DEFAULT_HOURS`. Same fail-open-to-defaults shape as
    `_tick004_rot_thresholds`/`_load_large_glob_max_files` -- a missing or
    malformed `frob.toml` degrades to the defaults rather than erroring."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return dict(_DISPATCH_STALE_DEFAULT_HOURS)
    try:
        with toml_path.open("rb") as handle:
            table = tomllib.load(handle).get("tickets", {})
        return {
            priority: float(
                table.get(f"dispatch_stale_{priority.value}_hours", default)
            )
            for priority, default in _DISPATCH_STALE_DEFAULT_HOURS.items()
        }
    except (OSError, tomllib.TOMLDecodeError, TypeError, ValueError) as exc:
        _log.warning(
            "tickets: dispatch-stale thresholds unreadable/malformed in %s (%s), "
            "using defaults",
            toml_path,
            exc,
        )
        return dict(_DISPATCH_STALE_DEFAULT_HOURS)


# frob:ticket T-0752
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours.test_same_day_is_zero_hours  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestDispatchStaleHours.test_one_day_old_is_24_hours  # noqa: E501
def dispatch_stale_hours(ticket: Ticket, *, today: date | None = None) -> float:
    """Hours `ticket` has been sitting since filing (T-0752's "last state
    change or filing" measurement) -- `Ticket.created` is the only
    timestamp this model carries (no per-transition history exists yet, so
    "last state change" degrades to "filing" here; a finer-grained
    transition timestamp is a follow-on, not built by this pass), converted
    from whole days to hours (`(today - ticket.created).days * 24`). `today`
    is injectable for deterministic tests; omitted, it defaults to
    `date.today()`."""
    if today is None:
        today = date.today()
    return (today - ticket.created).days * 24.0


# frob:ticket T-0752
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_dispatch_stale.py::TestUndispatchedStale.test_critical_past_threshold_alarms  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestUndispatchedStale.test_critical_under_threshold_no_alarm  # noqa: E501
# frob:tests tests/test_tickets_dispatch_stale.py::TestUndispatchedStale.test_medium_priority_never_alarms  # noqa: E501
def undispatched_stale(
    tickets: Sequence[Ticket],
    root: Path,
    *,
    today: date | None = None,
) -> tuple[tuple[Ticket, float, float], ...]:
    """`(ticket, hours_elapsed, threshold_hours)` for every CRITICAL/HIGH
    ticket in `tickets` whose `dispatch_stale_hours` has crossed its
    `_dispatch_stale_thresholds` entry (T-0752) -- the single staleness-
    alarm computation both `frob ticket doable`'s row rendering and a
    future TICK-family `frob check` gate (T-0714/T-0752 coordination, gate
    wiring itself is out of this ticket's declared scope --
    `src/frob/gates/**` -- and tracked separately) are meant to call, so
    the "past threshold" judgment lives in exactly one place. `tickets`
    should already be the DISPATCHABLE set (unblocked, unleased) -- this
    function does not itself re-derive that; pass `doable(...)`'s result
    filtered to non-in-flight rows (`has_live_lease`)."""
    thresholds = _dispatch_stale_thresholds(root)
    alarms: list[tuple[Ticket, float, float]] = []
    for t in tickets:
        threshold = thresholds.get(t.priority)
        if threshold is None:
            continue
        elapsed = dispatch_stale_hours(t, today=today)
        if elapsed > threshold:
            alarms.append((t, elapsed, threshold))
    return tuple(alarms)


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
# frob:ticket T-0561
# frob:ticket T-0422
# frob:waive COV005 reason="T-0485's docstring/signature edit to this already-private helper shifted line offsets against the many other symbols in this file sharing the frob:ticket T-0455 target; COV005's rebind check matches old/new bindings by (kind, target) alone across the whole file and reads the shift as a rebind onto a new private symbol -- this directive has bound _scope_add_conflicts (private) all along, same false-positive class as gates/__init__.py's own documented COV005 waiver"  # noqa: E501
# frob:tests tests/test_tickets_scope_mutation.py::TestNewFileCarveOut.test_new_file_under_broad_lease_is_exempt  # noqa: E501
# frob:tests tests/test_tickets_scope_mutation.py::TestNewFileCarveOut.test_existing_file_under_broad_lease_still_conflicts  # noqa: E501
# frob:tests tests/test_tickets_scope_mutation.py::TestNewFileCarveOut.test_new_file_exact_match_of_holder_scope_still_conflicts  # noqa: E501
def _scope_add_conflicts(
    glob: str,
    ticket_id: str,
    queue: dict[str, Ticket],
    own_scope: Sequence[str] = (),
    *,
    root: Path | None = None,
) -> tuple[str, str] | None:
    """`(holding_ticket_id, holder_glob)` if `glob` overlaps the declared
    scope of another IN_PROGRESS ticket (T-0453 lease model), or `None` if
    free to lease. Every OTHER in-progress ticket's FULL declared scope is
    checked (not breadth-demoted) -- an explicit `--add` request is a
    stronger claim than a passive `doable` listing, so this never silently
    lets an expansion into a busy over-broad lease through the same
    demotion `leased_by` applies for queue-display purposes.

    T-0485: before checking for contention, `glob` is exempted if it is a
    provable subset (`_glob_is_subset`) of ANY glob already in `own_scope`
    (the requesting ticket's OWN pre-mutation scope) -- narrowing an
    already-grandfathered-broad glob down to a concrete path it already
    covers can never create NEW contention, so it must never be refused as
    a fresh lease request against the same holder.

    T-0561: a broad, in-progress umbrella lease (a repo-wide epic like
    `tests/**`) used to reject EVERY other ticket's `--add` into that
    subtree outright, even a request that could not possibly touch any
    file the umbrella ticket is itself editing -- creating a brand-new
    file. When `root` is given and `glob` is a concrete literal path (no
    `*`/`?`/`[...]`) that does not yet exist on disk under `root`
    (`_is_new_concrete_file_glob`), a collision against a holder is
    downgraded from a hard reject to a pass UNLESS the colliding holder
    glob is that exact same literal path -- a real same-file race, still
    refused. This is a narrow, additive-file-only carve-out: it never
    exempts a wildcard-bearing `glob` (that could still claim an existing
    file the holder is mid-edit on) and never touches the `own_scope`
    subset check above."""
    if any(_glob_is_subset(glob, existing) for existing in own_scope):
        return None
    new_file = root is not None and _is_new_concrete_file_glob(glob, root)
    for holder in sorted(queue.values(), key=lambda t: t.id):
        if holder.id == ticket_id or holder.state is not TicketState.IN_PROGRESS:
            continue
        collision = scope_overlap_globs((glob,), holder.scope)
        if collision is not None:
            if new_file and collision[1] != glob:
                _log.info(
                    "tickets: %s --add %r exempted from %s's lease on %r "
                    "(T-0561: new file, holder glob is not an exact match)",
                    ticket_id,
                    glob,
                    holder.id,
                    collision[1],
                )
                continue
            return (holder.id, collision[1])
    return None


# frob:ticket T-0561
# frob:ticket T-0422
def _is_new_concrete_file_glob(glob: str, root: Path) -> bool:
    """Whether `glob` names ONE concrete, not-yet-existing TEST file under
    `root` -- the narrow T-0561 carve-out signal.

    Deliberately narrower than "any brand-new file anywhere": a bare
    does-not-exist-on-disk check alone cannot tell a genuine additive test
    file apart from a real expansion attempt into a busy module that
    merely hasn't been created YET (`src/frob/gates/foo.py` against an
    in-progress `src/frob/gates/**` lease is exactly the case
    `test_add_leased_path_rejected_names_holder` proves must still be
    refused) -- test fixtures routinely run against an empty `tmp_path`,
    where EVERY path "does not exist yet", so existence alone is not a
    safe signal outside a real checkout. Restricting to `frob.excludes.
    is_test_file` paths matches the ticket's actual repro (a new
    `tests/unit/test_*.py` file blocked by T-0160's `tests/**` epic
    lease) and keeps this carve-out from silently widening into
    production source."""
    if any(ch in glob for ch in "*?["):
        return False
    if not is_test_file(glob):
        return False
    return not (root / glob).exists()


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
# frob:ticket T-0561
# frob:ticket T-0422
# frob:waive COV005 reason="T-0485's caller-signature edit (own_scope passthrough to _scope_add_conflicts) shifted line offsets against the many other symbols in this file sharing the frob:ticket T-0455 target; COV005's rebind check matches old/new bindings by (kind, target) alone across the whole file and reads the shift as a rebind onto a new private symbol -- this directive has bound _validate_scope_mutation (private) all along, same false-positive class as gates/__init__.py's own documented COV005 waiver"  # noqa: E501
def _validate_scope_mutation(
    ticket_id: str,
    ticket: Ticket,
    queue: dict[str, Ticket],
    add_globs: tuple[str, ...],
    remove_globs: tuple[str, ...],
    *,
    root: Path | None = None,
) -> Result[None, TicketError]:
    """The per-glob FAIL-LOUD checks `mutate_scope` runs against the loaded
    ticket+queue (T-0455): a `remove` glob must be declared and evidence-
    free (`ScopeRemoveNotDeclared`/`ScopeRemoveOrphansEvidence`); an `add`
    glob must not overlap another in-progress ticket's lease
    (`ScopeLeaseConflict`, `_scope_add_conflicts`) -- unless T-0561's
    narrow new-concrete-file carve-out applies (`root` must be given for
    that check to run at all)."""
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
        conflict = _scope_add_conflicts(glob, ticket_id, queue, ticket.scope, root=root)
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
# frob:ticket T-0561
# frob:ticket T-0422
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

    T-0561: a concrete new-file `add` (no wildcard, does not yet exist on
    disk) is exempted from that conflict against a broader umbrella
    lease's ALREADY-existing files (`_scope_add_conflicts`'s narrow
    carve-out) -- creating a brand-new file cannot collide with edits to
    files that already exist.

    Held under `ledger_lock` end to end (load, validate, write) so this can
    never interleave with a concurrent ledger mutation (T-0458 single-writer
    invariant) -- no hand-edit of `tickets.md` is ever involved.
    """
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
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
            ticket_id, ticket, queue, add_globs, remove_globs, root=root
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


# frob:ticket T-0411
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_priority.py::TestSetPriority.test_updates_priority_field
def set_priority(
    root: Path, ticket_id: str, priority: Priority
) -> Result[Ticket, TicketError]:
    """Set `ticket_id`'s `priority` field (T-0411) -- the accountable,
    single-writer way to reprioritize a ticket instead of hand-editing
    `tickets.md` frontmatter. Held under `ledger_lock` (same discipline as
    `mutate_scope`) so this can never interleave with a concurrent ledger
    mutation. A no-op write (still logged) if `priority` already matches."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        updated = ticket.model_copy(update={"priority": priority})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: %s priority set to %s", ticket_id, priority.value)
    return Ok(updated)


# frob:ticket T-0834
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_ticket_evidence.py::TestSetKind.test_updates_kind_field
def set_kind(
    root: Path, ticket_id: str, kind: TicketKind
) -> Result[Ticket, TicketError]:
    """Set `ticket_id`'s `kind` field (T-0834) -- the accountable,
    single-writer way to correct a mis-filed kind instead of hand-editing
    `tickets.md` frontmatter, same ledger-locked, no-terminal-state-check
    pattern `set_priority` uses. A no-op write (still logged) if `kind`
    already matches."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        updated = ticket.model_copy(update={"kind": kind})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: %s kind set to %s", ticket_id, kind.value)
    return Ok(updated)


# frob:ticket T-0715
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_tiers.py::TestSprintAssign.test_updates_sprint_field
def set_sprint(
    root: Path, ticket_id: str, sprint: str | None
) -> Result[Ticket, TicketError]:
    """`frob ticket sprint assign <id> <label>`: set `ticket_id`'s `sprint`
    field (T-0715) -- the same single-writer, ledger-locked pattern
    `set_component` uses. `sprint=None` clears it back to uncommitted/
    backlog."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        updated = ticket.model_copy(update={"sprint": sprint})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: %s sprint set to %s", ticket_id, sprint)
    return Ok(updated)


# frob:ticket T-0715
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_tiers.py::TestSprintShow.test_state_rollup_and_velocity
def sprint_view(queue: TicketQueue, sprint: str) -> SprintReport:
    """`frob ticket sprint show <label>`: every ticket committed to
    `sprint` (T-0715), a `TicketState -> count` rollup, and `closed`
    (done-count, the mandate's "closed-count velocity" -- derived from
    current ledger state, not a separate tracked counter). Always returns
    a report, even when no ticket carries this sprint label (`tickets`
    empty, every rollup count zero) -- there is no NotFound case, a sprint
    label is a free-form tag, not an id that must resolve."""
    tickets = tuple(
        sorted(
            (t for t in queue.tickets.values() if t.sprint == sprint),
            key=lambda t: t.id,
        )
    )
    rollup: dict[TicketState, int] = {}
    for t in tickets:
        rollup[t.state] = rollup.get(t.state, 0) + 1
    closed = rollup.get(TicketState.DONE, 0)
    return SprintReport(sprint=sprint, tickets=tickets, rollup=rollup, closed=closed)


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_organization.py::TestSetComponent.test_updates_component_field  # noqa: E501
def set_component(
    root: Path, ticket_id: str, component: str | None
) -> Result[Ticket, TicketError]:
    """Set `ticket_id`'s `component` field (T-0454) -- which module/area this
    ticket belongs to, the same single-writer, ledger-locked pattern
    `set_priority` uses. `component=None` clears it back to uncategorized."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        updated = ticket.model_copy(update={"component": component})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info("tickets: %s component set to %s", ticket_id, component)
    return Ok(updated)


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_organization.py::TestMutateLabels.test_add_and_remove_labels  # noqa: E501
def mutate_labels(
    root: Path,
    ticket_id: str,
    *,
    add: Sequence[str] = (),
    remove: Sequence[str] = (),
) -> Result[Ticket, TicketError]:
    """Add/remove freeform `labels` on `ticket_id` (T-0454) -- orthogonal to
    `scope`'s lease-aware `mutate_scope`: a label is a plain organizational
    tag, never a filesystem glob, so it carries no lease-conflict check and
    no audit trail the way a scope mutation does. `add`/`remove` may be
    combined in one call; each is comma-split the same way `scope`/`labels`
    entries always are (`_split_scope_entries`, T-0241's normalization
    reused here). A no-op call (nothing to add or remove) is an error --
    same "don't call this for nothing" discipline `mutate_scope` enforces."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    add_labels = _normalize_scope_entries(tuple(add))
    remove_labels = _normalize_scope_entries(tuple(remove))
    if not add_labels and not remove_labels:
        return Err(TicketError.LabelChangeEmpty)
    with ledger_lock(root):
        loaded = _load_ticket_and_queue(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket, _queue = loaded.danger_ok
        new_labels = tuple(lbl for lbl in ticket.labels if lbl not in remove_labels)
        for label in add_labels:
            if label not in new_labels:
                new_labels += (label,)
        updated = ticket.model_copy(update={"labels": new_labels})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s labels changed (+%d/-%d), now %s",
        ticket_id,
        len(add_labels),
        len(remove_labels),
        list(updated.labels),
    )
    return Ok(updated)


# frob:ticket T-0409
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestClosedTicketIds.test_returns_done_and_dropped_only  # noqa: E501
def closed_ticket_ids(queue: TicketQueue) -> tuple[str, ...]:
    """Ids in `queue` (whatever store it was loaded from -- active-only or
    merged) whose state is DONE or DROPPED, oldest-first (T-0409): the
    ledger-hygiene gate's (TICK003, `frob.gates.tickets_gate`) building
    block for "how many closed tickets are sitting un-archived" -- called
    with `load_active`'s active-only queue there, since an ARCHIVED closed
    ticket is by definition no longer a hygiene problem. Kept here (not
    computed inline in `frob.gates`) so the "closed" predicate has exactly
    one definition, reused by anything that needs to answer the same
    question (`frob ticket archive`'s own move-eligibility check already
    uses the equivalent inline predicate; this is the reusable, testable
    form of it)."""
    closed = [
        t
        for t in queue.tickets.values()
        if t.state in (TicketState.DONE, TicketState.DROPPED)
    ]
    return tuple(t.id for t in sorted(closed, key=lambda t: (t.created, t.id)))


# frob:ticket T-0411
# frob:tests tests/test_tickets_priority.py::TestDoablePriorityOrdering.test_high_priority_surfaces_before_older_low_priority  # noqa: E501
def _doable_sort_key(t: Ticket) -> tuple[int, date, str]:
    """`doable`/`doable_blocked` ordering key (T-0411): highest PRIORITY_RANK
    first, then oldest-created, then id -- priority is the primary axis so a
    high-value ticket never rots behind a pile of older low-value ones, with
    age still breaking ties within the same priority (the prior behavior for
    tickets that were all effectively MEDIUM)."""
    return (-PRIORITY_RANK[t.priority], t.created, t.id)


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_organization.py::TestBoardView.test_columns_in_fixed_order  # noqa: E501
def board_view(
    queue: TicketQueue,
    *,
    component: str | None = None,
    label: str | None = None,
) -> tuple[BoardColumn, ...]:
    """`frob ticket board`: every ticket grouped into `BOARD_STATES` columns,
    each priority-then-age ordered (`_doable_sort_key`, T-0411) -- a
    priority-ordered, at-a-glance view of the whole queue instead of one
    flat id-ordered list (T-0454). Optional `component`/`label` filters
    narrow to one area/tag; a ticket must match BOTH when both are given.
    Every column is always present, even empty, so the shape of the board
    never depends on what happens to be in flight right now."""
    tickets = list(queue.tickets.values())
    if component is not None:
        tickets = [t for t in tickets if t.component == component]
    if label is not None:
        tickets = [t for t in tickets if label in t.labels]
    columns = []
    # frob:waive PERF004 reason="one sorted() call per BOARD_STATES entry -- a fixed 6-iteration loop over the queue's own ticket count, not an unbounded hoisted-sort opportunity"  # noqa: E501
    for state in BOARD_STATES:
        in_state = sorted(
            (t for t in tickets if t.state is state), key=_doable_sort_key
        )
        columns.append(BoardColumn(state=state, tickets=tuple(in_state)))
    return tuple(columns)


# frob:ticket T-0454
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_organization.py::TestEpicRollup.test_counts_done_and_total  # noqa: E501
def epic_rollup(queue: TicketQueue, epic_id: str) -> Result[EpicRollup, TicketError]:
    """`frob ticket epic <id>`: the full descendant subtree of `epic_id` via
    the `parent` chain (any depth, not just direct children), plus a
    done/total rollup and the ids of any LEAF descendant (no children of
    its own) that is currently BLOCKED -- the two things a human scanning
    an epic wants first, computed once instead of hand-counted (T-0454).
    `NotFound` if `epic_id` itself does not resolve in `queue`."""
    epic = queue.tickets.get(epic_id)
    if epic is None:
        return Err(TicketError.NotFound)
    children_of: dict[str, list[Ticket]] = {}
    for t in queue.tickets.values():
        if t.parent is not None:
            children_of.setdefault(t.parent, []).append(t)
    descendants: list[Ticket] = []
    frontier = [epic_id]
    seen = {epic_id}
    while frontier:
        current = frontier.pop()
        for child in children_of.get(current, ()):
            if child.id in seen:
                continue
            seen.add(child.id)
            descendants.append(child)
            frontier.append(child.id)
    done = sum(1 for t in descendants if t.state is TicketState.DONE)
    blocked_leaves = tuple(
        t.id
        for t in descendants
        if t.state is TicketState.BLOCKED and t.id not in children_of
    )
    # frob:waive PERF004 reason="single sorted() call over the finished descendants list, not inside the BFS while-loop above it -- the checker's whole-function loop scan flags it textually, not per-iteration"  # noqa: E501
    return Ok(
        EpicRollup(
            epic=epic,
            descendants=tuple(sorted(descendants, key=lambda t: t.id)),
            done=done,
            total=len(descendants),
            blocked_leaves=blocked_leaves,
        )
    )


# frob:ticket T-0568
# frob:doc docs/modules/tickets.md#frob-ticket-brief-t-0568
# frob:tests tests/test_tickets_brief.py::TestBriefTicket.test_composes_full_briefing
def brief_ticket(root: Path, ticket_id: str) -> Result[str, TicketError]:
    """`frob ticket brief <id>` (T-0568): compose the complete agent
    mission briefing text (`frob.tickets._brief.compose_brief`) for
    `ticket_id` -- replacing the ~400 words of hand-typed dispatch
    boilerplate a coordinator otherwise repeats per ticket. `Err(NotFound)`
    if `ticket_id` does not resolve."""
    from frob.tickets._brief import compose_brief

    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    queue_result = load_queue(root)
    holders: tuple[tuple[str, str], ...] = ()
    if queue_result.is_ok:
        holders = leased_by(queue_result.danger_ok, ticket, root)

    return Ok(compose_brief(root, ticket, holders))


# frob:ticket T-0453
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_lease.py::TestDoable.test_ignore_lease_returns_raw_list
# frob:tests tests/test_tickets_tiers.py::TestDoableLeafOnly.test_epic_and_story_never_surface  # noqa: E501
# frob:waive DRIFT001 reason="T-0453 added root/ignore_lease params; frob.lock ack out of scope, no inline-waivable syntax for JSON -- reviewer re-acks at land"  # noqa: E501
# frob:invariant INV-024
# frob:ticket T-0715
def doable(
    queue: TicketQueue,
    root: Path | None = None,
    *,
    ignore_lease: bool = False,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> tuple[Ticket, ...]:
    """Tickets in {queued, planned} with no open blockers, ordered by
    priority (highest first, T-0411) then oldest-first within a priority tier.

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

    T-0773: `_all_leases(queue, root)` is computed ONCE here and threaded
    through every `leased_by` call in the filter loop below (same pattern
    as `breadth`), instead of each candidate re-deriving the union of
    local-ledger and cross-worktree leases for itself.

    T-0752: pass a precomputed `breadth` (`scope_breadth_context(root)`,
    the same kwarg `doable_blocked` already accepts) when the caller has
    already walked the tree for it -- omitting it while `root` is given
    computes it internally, same default-to-internal convention as
    `doable_blocked`. This is what keeps `frob ticket doable`'s default
    render (which also needs `breadth` for its own warnings) down to a
    single `git ls-files` walk instead of two.
    """
    candidates = _doable_candidates(queue)
    if not ignore_lease:
        if root is not None and breadth is None:
            breadth = scope_breadth_context(root)
        all_leases = _all_leases(queue, root)
        candidates = [
            t
            for t in candidates
            if not leased_by(queue, t, root, breadth=breadth, all_leases=all_leases)
        ]
    return tuple(sorted(candidates, key=_doable_sort_key))


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
    (re-walking the tree when the caller already has one). T-0773:
    `_all_leases(queue, root)` is likewise computed ONCE here and threaded
    through every `leased_by` call below, rather than each candidate
    re-deriving it."""
    candidates = _doable_candidates(queue)
    if root is not None and breadth is None:
        breadth = scope_breadth_context(root)
    all_leases = _all_leases(queue, root)
    blocked: list[tuple[Ticket, tuple[tuple[str, str], ...]]] = []
    for t in sorted(candidates, key=_doable_sort_key):
        hits = leased_by(queue, t, root, breadth=breadth, all_leases=all_leases)
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
# T-0524: frob:doc removed -- this is a thin wrapper delegating to
# has_substantive_done_report (frob.tickets._models), which already
# carries the same docs/modules/tickets.md#public-api anchor; a second
# copy on this private pass-through was redundant (COV007).
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


# frob:ticket T-0417
def _transition_guard(
    root: Path,
    ticket: Ticket,
    to: TicketState,
    queue: dict[str, Ticket],
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
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
        return _done_transition_guard(
            root,
            ticket,
            queue,
            covers_scope=covers_scope,
            reviewed=reviewed,
            mutation_evidence=mutation_evidence,
            evidence_reverified=evidence_reverified,
        )
    return Ok(None)


# frob:ticket T-0715
def _open_descendant_ids(ticket: Ticket, queue: dict[str, Ticket]) -> tuple[str, ...]:
    """Ids of every descendant of `ticket` (via the `parent` chain, any
    depth) whose state is not done/dropped -- the T-0715 structural rule an
    EPIC/STORY's DONE transition enforces: it cannot close while any
    descendant is still open. Mirrors `epic_rollup`'s own parent-chain BFS
    (kept separate: that one builds a full rollup for display, this is a
    cheap open/closed check for a single guard)."""
    children_of: dict[str, list[Ticket]] = {}
    for t in queue.values():
        if t.parent is not None:
            children_of.setdefault(t.parent, []).append(t)
    open_ids: list[str] = []
    frontier = [ticket.id]
    seen = {ticket.id}
    while frontier:
        current = frontier.pop()
        for child in children_of.get(current, ()):
            if child.id in seen:
                continue
            seen.add(child.id)
            if child.state in _OPEN_STATES:
                open_ids.append(child.id)
            frontier.append(child.id)
    return tuple(sorted(open_ids))


# T-0215 review round 2: a cmd: entry is only ever valid evidence on a
# docs-kind ticket (COV003 mirrors this at check time). Re-check HERE too,
# not just at add_cmd_evidence write time -- a ticket's kind can be
# hand-edited after evidence was recorded, or a cmd: entry can be
# hand-pasted directly into the ledger, either of which would otherwise
# slip a code-kind ticket through close on unverifiable evidence.
# frob:ticket T-0417
# frob:ticket T-0976
def _done_transition_structural_guard(
    ticket: Ticket, queue: dict[str, Ticket], *, covers_scope: bool | None
) -> Result[None, TicketError]:
    """`_done_transition_guard`'s structural (non-diff-derived) checks:
    evidence + Done report present, open descendants, disallowed cmd:
    evidence, injected `covers_scope`, and unbound acceptance criteria --
    split from its review/mutation/reverify/diff-derived checks."""
    if not ticket.evidence or not _has_done_report(ticket.body):
        _log.warning(
            "tickets: %s cannot close, missing evidence or a substantive Done report",
            ticket.id,
        )
        return Err(TicketError.MissingEvidence)
    if ticket.tier is not TicketTier.TICKET:
        open_descendants = _open_descendant_ids(ticket, queue)
        if open_descendants:
            _log.warning(
                "tickets: %s (tier=%s) cannot close, open descendant(s): %s",
                ticket.id,
                ticket.tier,
                open_descendants,
            )
            return Err(TicketError.OpenDescendant)
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
    unbound = unbound_acceptance(ticket)
    if unbound:
        _log.warning(
            "tickets: %s cannot close, unbound acceptance criterion/criteria: %s",
            ticket.id,
            [c.text for c in unbound],
        )
        return Err(TicketError.AcceptanceUnbound)
    return Ok(None)


def _done_transition_guard(
    root: Path,
    ticket: Ticket,
    queue: dict[str, Ticket],
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
) -> Result[None, TicketError]:
    """Enforce DONE-transition preconditions: evidence + substantive Done
    report present, no cmd: evidence on a kind that disallows it, (T-0715)
    an EPIC/STORY refuses to close while any descendant (via the `parent`
    chain) is still open, (D-02,
    when the caller supplies `covers_scope`) at least one evidence id binds
    to a touched/scope symbol, (T-0572) every declared acceptance criterion
    has at least one resolving evidence id -- see `unbound_acceptance` (a
    ticket with an empty `acceptance` list is unaffected, T-0572 backward
    compat) -- (T-0571, when the caller supplies `reviewed`) at least
    one approve-verdict review record naming the current commit, (T-0844,
    when the caller supplies `mutation_evidence=False`) that the ticket
    does not carry an unwaived ERROR-severity TEST016 confirmatory-only-
    evidence finding, mirroring `frob.tickets._land._check_mutation_
    evidence`'s land-time refusal so a security/bug ticket closed directly
    (never landed) is not exempt from the same obligation, (T-0417 N-02,
    when the caller supplies `evidence_reverified=False`) that a fresh
    re-run of the ticket's own non-cmd evidence ids against the CURRENT
    tree still passes -- closing must never trust a stale record-time
    "passed" observation the way `land`'s own `_reverify_evidence_post_
    merge` already refuses to for the merge path (D-05); this is the
    direct-close twin of that same obligation, and (T-0854,
    ALWAYS, not injected) that no registry disposition or waiver still
    cites `ticket.id` as its live tracker (`frob.tickets._live_tracker.
    live_tracker_citations`) -- the T-0605-orphaned-41-rows incident class.

    `covers_scope`/`reviewed`/`mutation_evidence`/`evidence_reverified` are
    injected, never computed here: answering "does an evidence id cover a
    touched/scope symbol" needs the obligation graph (`frob.graph`) and the
    `TESTS`-edge index `frob.testing`/`frob.gates` already build, answering
    "is there an approve review naming HEAD" needs `git rev-parse` under
    the caller's root, answering "did the bound evidence kill a mutant"
    needs `frob.gates.mutation_evidence_violations`, and answering "does
    the evidence still pass right now" needs a real test-runner spawn --
    `frob.tickets` deliberately stays free of all four dependencies
    (docs/rework.md cycle-avoidance -- `frob.gates`/`frob.app` are the
    layers allowed to join graph/runner + tickets). `None` (the default,
    matching every caller before D-02/T-0571/T-0844/T-0417) skips each
    check entirely, so existing callers/tests are unaffected; a caller
    with the needed context (`frob.gates.evidence_covers_scope`,
    `has_approved_review_for_commit`, `frob.gates.mutation_evidence_
    violations`, `frob.app.ticket_runner._reverify_evidence_for_close`, or
    its own equivalent) opts in by passing an explicit `True`/`False`.
    `live_tracker_citations`, by contrast, is a plain `git
    grep` under `root` (against `current_branch(root)` as the diff base,
    T-0854 rework's diff-aware exemption -- see the module docstring in
    `frob.tickets._live_tracker`) -- cheap enough (T-0854's own PERF
    guard: "a targeted grep-shaped scan, not a full registry parse per
    close") to run unconditionally here, so every caller (direct `frob
    ticket close` and `land`'s own post-merge finalize call) gets it for
    free with no injection plumbing to wire; an unresolvable branch (not a
    git work tree) degrades to skipping the check, matching T-0844's own
    `_close_mutation_evidence_for_ticket` posture for the identical
    failure mode."""
    structural = _done_transition_structural_guard(
        ticket, queue, covers_scope=covers_scope
    )
    if structural.is_err:
        return structural
    if reviewed is False:
        _log.warning(
            "tickets: %s cannot close --strict, no approve-verdict review "
            "record names the current commit",
            ticket.id,
        )
        return Err(TicketError.MissingApprovedReview)
    if mutation_evidence is False:
        _log.warning(
            "tickets: %s cannot close, confirmatory-only evidence (TEST016 "
            "ERROR) for kind=%s -- strengthen the named evidence tests or "
            "retry with --skip-mutation-evidence",
            ticket.id,
            ticket.kind,
        )
        return Err(TicketError.EvidenceConfirmatoryOnly)
    if evidence_reverified is False:
        _log.warning(
            "tickets: %s cannot close, a fresh re-run of its own recorded "
            "evidence against the current tree did not pass -- the "
            "work was tested once but has since regressed; fix the break "
            "or re-record evidence (`frob ticket evidence %s <node-id>...`) "
            "and retry",
            ticket.id,
            ticket.id,
        )
        return Err(TicketError.EvidenceNotPassing)
    return _done_transition_diff_derived_guard(root, ticket)


# frob:ticket T-0976
def _done_transition_diff_derived_guard(
    root: Path, ticket: Ticket
) -> Result[None, TicketError]:
    """`_done_transition_guard`'s two diff-derived, ALWAYS-run (not
    injected) DONE-transition checks: T-0854's live-tracker-citation
    refusal, and T-0756's new-gate-rule-needs-acceptance refusal. Both
    resolve `current_branch(root)` once and degrade to skipping the check
    when it is unresolvable (not a git work tree), matching this module's
    other diff-derived checks' failure posture."""
    from frob.gitio import current_branch

    branch = current_branch(root)
    citations = (
        live_tracker_citations(root, ticket.id, base_ref=branch.danger_ok)
        if branch.is_ok
        else ()
    )
    if citations:
        _log.warning(
            "tickets: %s cannot close, %d site(s) still cite it as their "
            "live tracker (registry deferred:/tracked_by: disposition or a "
            "waiver ticket= attribute): %s -- file a successor ticket and "
            "re-point these rows, or re-point them in this same change",
            ticket.id,
            len(citations),
            list(citations),
        )
        return Err(TicketError.LiveTrackerCited)
    new_rule_ids = (
        new_gate_rule_ids(root, base_ref=branch.danger_ok) if branch.is_ok else ()
    )
    unaccepted = missing_acceptance_for_new_rules(ticket, new_rule_ids or ())
    if unaccepted:
        _log.warning(
            "tickets: %s cannot close, adds new gate rule id(s) %s with no "
            "bound before-fails/after-passes fixture acceptance criterion "
            "(T-0756) -- record one proving the rule fires through the "
            "production invocation, then retry",
            ticket.id,
            list(unaccepted),
        )
        return Err(TicketError.NewGateRuleUnaccepted)
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


# frob:ticket T-0976
def _recover_missing_evidence_for_done(
    root: Path,
    ticket_id: str,
    ticket: Ticket,
    queue: dict[str, Ticket],
    to: "TicketState",
) -> tuple[Ticket, dict[str, Ticket]]:
    """T-0357 best-effort evidence recovery for `transition`: a ticket
    closed straight from a hand-merged worktree (bypassing `frob ticket
    land`'s ledger splice) can arrive with an empty structured `evidence:`
    field even though its Done report prose already carries the rendered
    ids -- replay it before the DONE guard would otherwise reject as
    MissingEvidence. A no-op (returns `(ticket, queue)` unchanged) unless
    `to` is DONE, evidence is already empty is false, or the replay
    itself fails."""
    if to != TicketState.DONE or ticket.evidence:
        return ticket, queue
    replayed = replay_evidence_from_done_report(root, ticket_id)
    if replayed.is_err:
        return ticket, queue
    recovered = replayed.danger_ok
    updated_queue = dict(queue)
    updated_queue[ticket_id] = recovered
    return recovered, updated_queue


# frob:invariant INV-002
# invariant spec: [INV-002](invariants/INV-002.md)
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose.test_transition_rejects_when_mutation_evidence_false  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose.test_transition_allows_when_mutation_evidence_true  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0844MutationEvidenceOnClose.test_transition_permissive_when_mutation_evidence_none  # noqa: E501
# frob:tests tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard.test_epic_close_refused_with_open_descendant  # noqa: E501
# frob:tests tests/test_tickets_tiers.py::TestCloseOpenDescendantGuard.test_epic_close_allowed_once_descendant_done  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_rejects_when_evidence_reverified_false  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_allows_when_evidence_reverified_true  # noqa: E501
# frob:tests tests/test_evidence_integrity.py::TestT0417ReverifyEvidenceOnClose.test_transition_permissive_when_evidence_reverified_none  # noqa: E501
# frob:ticket T-0715
# frob:ticket T-0417
# frob:waive AFFECT001 reason="T-0976 pure internal refactor: extraction of _recover_missing_evidence_for_done from this already-documented function, no external contract/behavior change, doc anchor(s) remain accurate as-is"  # noqa: E501
def transition(
    root: Path,
    ticket_id: str,
    to: TicketState,
    *,
    covers_scope: bool | None = None,
    reviewed: bool | None = None,
    mutation_evidence: bool | None = None,
    evidence_reverified: bool | None = None,
) -> Result[Ticket, TicketError]:
    """Enforce the state machine; `done` also requires evidence and a
    substantive Done report, (D-02) an evidence id covering a touched/
    scope symbol whenever the caller supplies `covers_scope=False`,
    (T-0571) an approve-verdict review record naming the current commit
    whenever the caller supplies `reviewed=False`, (T-0844) refuses on
    an unwaived ERROR-severity TEST016 confirmatory-only-evidence finding
    whenever the caller supplies `mutation_evidence=False`, and (T-0417
    N-02) refuses when a fresh re-run of the ticket's recorded evidence
    against the CURRENT tree no longer passes, whenever the caller
    supplies `evidence_reverified=False` (see `_done_transition_guard`'s
    docstring for why these are injected rather than computed here)."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_ticket_and_queue(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket, queue = loaded.danger_ok
    ticket, queue = _recover_missing_evidence_for_done(
        root, ticket_id, ticket, queue, to
    )

    allowed = _TRANSITIONS.get(ticket.state, frozenset())
    if to not in allowed:
        _log.warning(
            "tickets: %s illegal transition %s -> %s", ticket_id, ticket.state, to
        )
        return Err(TicketError.InvalidTransition)

    guard = _transition_guard(
        root,
        ticket,
        to,
        queue,
        covers_scope=covers_scope,
        reviewed=reviewed,
        mutation_evidence=mutation_evidence,
        evidence_reverified=evidence_reverified,
    )
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
# frob:waive ARCH001 reason="a typani Result guard chain (lease, schema, resolution, pass-check, then acceptance-range) where each stage is already its own dedicated helper (_check_evidence_resolution, _check_evidence_passing, ...); the length is the sequence of early-return guard calls itself, matching this module's own idiomatic and_then style -- splitting further would just rename the same guard clauses behind a second layer of indirection"  # noqa: E501
def add_evidence(
    root: Path,
    ticket_id: str,
    node_ids: Sequence[str],
    collected: frozenset[str] | None = None,
    passed: frozenset[str] | None = None,
    accepts: Sequence[int] | None = None,
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
    see `add_cmd_evidence`/`reverify_cmd_evidence`).

    `accepts` (T-0572) is a list of 0-based `ticket.acceptance` indices:
    every `node_ids` entry is ALSO bound onto each named acceptance
    criterion's own `evidence` tuple, in the same write as the evidence-list
    append -- the CLI surface for closing the "closed but not what was
    asked" hole (`--accepts N` on `frob ticket evidence`/`close`).
    `accepts=None` (default) binds nothing, matching every caller before
    T-0572. An out-of-range index rejects the whole batch
    (`Err(AcceptanceIndexOutOfRange)`) before anything is written -- a
    typo'd index must never silently bind evidence to the wrong criterion
    or to nothing at all."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
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

    if accepts is not None:
        out_of_range = [i for i in accepts if i < 0 or i >= len(ticket.acceptance)]
        if out_of_range:
            _log.warning(
                "tickets: %s --accepts index/indices out of range %s "
                "(ticket has %d acceptance item(s))",
                ticket_id,
                out_of_range,
                len(ticket.acceptance),
            )
            return Err(TicketError.AcceptanceIndexOutOfRange)

    return _append_evidence_and_write(root, ticket, ticket_id, normalized_ids, accepts)


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
    root: Path,
    ticket: Ticket,
    ticket_id: str,
    node_ids: Sequence[str],
    accepts: Sequence[int] | None = None,
) -> Result[Ticket, TicketError]:
    """Merge new `node_ids` into `ticket.evidence` (deduplicated), bind them
    onto each `accepts`-named acceptance criterion's own `evidence` tuple
    (T-0572, also deduplicated), and write the updated ticket in one atomic
    write -- the append and the acceptance binding are never split across
    two writes, so a crash between them can never leave evidence recorded
    without its acceptance mapping (or vice versa)."""
    merged = ticket.evidence + tuple(
        nid for nid in node_ids if nid not in ticket.evidence
    )
    acceptance = ticket.acceptance
    if accepts:
        acceptance = tuple(
            c.model_copy(
                update={
                    "evidence": c.evidence
                    + tuple(nid for nid in node_ids if nid not in c.evidence)
                }
            )
            if i in accepts
            else c
            for i, c in enumerate(acceptance)
        )
    updated = ticket.model_copy(update={"evidence": merged, "acceptance": acceptance})
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
def run_cmd_evidence(command: str, cwd: Path | None = None) -> Result[str, TicketError]:
    """Run `command` as an argv (no shell, T-0805) and fold its outcome
    into one evidence string (`cmd:<command> exit=0 sha256=<12-hex>`) --
    the non-pytest
    evidence primitive `add_cmd_evidence` records for docs/design tickets
    (T-0215). A nonzero exit or a command that fails to launch at all is
    Err(EvidenceCmdFailed): a broken or never-run command can never
    masquerade as evidence just by being named. The digest is taken over
    stdout only (deterministic across whitespace-only stderr noise) so the
    same command run twice against the same repo state records the same
    entry instead of appending a new one every time.

    `cwd` (T-0834) is where `command` is actually run -- `add_cmd_evidence`
    passes the ticket's resolved `--path` root so a relative-path probe
    (`grep`/`test` over ticket scope files) runs against the worktree the
    evidence claim is ABOUT, not whatever directory happened to invoke the
    CLI. `None` (the `reverify_cmd_evidence` re-check path) keeps the
    previous behavior of inheriting the current process cwd.
    """
    completed = _run_evidence_command(command, cwd=cwd)
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
    cwd: Path | None = None,
) -> Result[subprocess.CompletedProcess, TicketError]:
    """Spawn `command` as an argv (never through a shell) and return its
    completed process; `Err(EvidenceCmdFailed)` if it fails to parse, fails
    to launch, or exits nonzero.

    `cwd` (T-0834) is forwarded straight to `guarded_subprocess_run`/
    `subprocess.run`; `None` inherits the current process's cwd (the
    pre-T-0834 default, still used by `reverify_cmd_evidence`). A relative-
    path command (a `grep`/`test` probe over ticket scope files) is only
    meaningful relative to the ticket's own worktree, not wherever the CLI
    happened to be invoked from -- see `run_cmd_evidence`.

    T-0805: previously ran `command` with `shell=True` -- ticket YAML
    (`cmd:` evidence entries) is repo-writable by any agent/tool, so a
    string handed to a shell is an injection-adjacent surface, not a
    hardened one, even though evidence commands are a sanctioned feature
    (T-0215). A survey of every `cmd:` entry actually recorded in
    `tickets.md`/`tickets-archive.md` at the time of this fix found five
    distinct commands; four are plain argv (`grep -n ...`, `grep -q ...`,
    `python3 <script>`, `uv run frob check --only docblocks`) and parse
    unchanged under `shlex.split`. Exactly one (an already-closed,
    archived ticket's evidence, `test "$(grep -c ...)" = N && test ...`)
    relies on shell command substitution and `&&` sequencing and cannot be
    expressed as a single argv; that entry is dead (its ticket is `done`,
    nothing re-verifies it live) and is the documented migration case --
    future evidence needing multi-step or substitution logic should shell
    out to a checked-in script (`cmd:python3 <script>` or
    `cmd:bash <script>`) invoked as a single argv entry instead of relying
    on inline shell syntax.

    Routed through `guarded_subprocess_run` (T-0778) so `FROB_DISABLE_EXEC`
    stops evidence commands too, not just `frob check`'s own tool runners.
    """
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        _log.error(
            "tickets: evidence command %r failed to parse as argv: %s", command, exc
        )
        return Err(TicketError.EvidenceCmdFailed)
    if not argv:
        _log.error("tickets: evidence command %r parsed to an empty argv", command)
        return Err(TicketError.EvidenceCmdFailed)
    try:
        guarded = guarded_subprocess_run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            cwd=cwd,
        )
    except OSError as exc:
        _log.error(
            "tickets: evidence command %r failed to launch (cwd=%s): %s",
            command,
            cwd,
            exc,
        )
        return Err(TicketError.EvidenceCmdFailed)
    if guarded.is_err:
        _log.error(
            "tickets: evidence command %r refused: %s", command, guarded.danger_err
        )
        return Err(TicketError.EvidenceCmdFailed)
    completed = guarded.danger_ok
    if completed.returncode != 0:
        _log.warning(
            "tickets: evidence command %r exited %d (cwd=%s, stderr tail: %r)",
            command,
            completed.returncode,
            cwd,
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
    root: Path,
    ticket_id: str,
    command: str,
    accepts: Sequence[int] | None = None,
) -> Result[Ticket, TicketError]:
    """Kind-gated non-pytest evidence channel (T-0215): runs `command` via
    `run_cmd_evidence` and appends the resulting entry to `ticket_id`'s
    structured evidence list. Only tickets whose `kind` is in
    `CMD_EVIDENCE_ALLOWED_KINDS` (currently just `docs`) may use this --
    code-kind tickets (bug/feature/security/ux/invariant/incident) always
    still require real pytest node ids via `add_evidence`, enforced here
    with Err(EvidenceKindNotAllowed) so a code change can never close on an
    unrelated shell command's exit status alone.

    `accepts` (T-0796) mirrors `add_evidence`'s acceptance-binding: a list
    of 0-based `ticket.acceptance` indices the recorded cmd-evidence entry
    is ALSO bound onto, in the same write as the evidence-list append. Its
    validation is identical to `add_evidence` -- an out-of-range index
    rejects the whole call (`Err(AcceptanceIndexOutOfRange)`) before
    anything is written. Before T-0796 this parameter did not exist, so
    `--accepts` passed alongside `--evidence-cmd` on the CLI was silently
    dropped and docs-kind tickets closed with UNBOUND acceptance despite
    the operator's explicit binding request.
    """
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    kind_check = _check_cmd_evidence_kind(ticket_id, ticket.kind)
    if kind_check.is_err:
        return Err(kind_check.danger_err)

    if accepts is not None:
        out_of_range = [i for i in accepts if i < 0 or i >= len(ticket.acceptance)]
        if out_of_range:
            _log.warning(
                "tickets: %s --accepts index/indices out of range %s "
                "(ticket has %d acceptance item(s))",
                ticket_id,
                out_of_range,
                len(ticket.acceptance),
            )
            return Err(TicketError.AcceptanceIndexOutOfRange)

    # T-0834: run the command from the ticket's own resolved `--path` root,
    # not the invoking process's cwd -- the evidence claim is about the
    # worktree named by `root`, and a relative-path probe (grep/test over
    # scope files) silently ran against whatever directory happened to
    # invoke the CLI before this, with no indication of which cwd it used.
    recorded = run_cmd_evidence(command, cwd=root)
    if recorded.is_err:
        return Err(recorded.danger_err)
    entry = recorded.danger_ok

    return _append_evidence_and_write(root, ticket, ticket_id, (entry,), accepts)


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


# frob:ticket T-0357
_EVIDENCE_LINE_RE = re.compile(r"^- `([^`]+)` \((?:pytest node id|cmd evidence)")


def _parse_evidence_ids_from_done_report(body: str) -> tuple[str, ...]:
    """Recover evidence ids from a ticket's rendered '## Done report' ->
    '### Evidence' section text, the inverse of `render_evidence_block`
    (T-0357). A worktree's structured `evidence:` field is the source of
    truth in the ordinary case; this exists only for the recovery path
    where that field is empty (or was lost by a hand-merge that bypassed
    the ledger splice) but the committed Done report prose still carries
    the rendered ids -- so a coordinator merging a worktree branch by hand
    (`git merge --no-ff` + `frob ticket close` on main, T-0248/T-0266) is
    never stuck re-typing node ids by hand. Returns ids in the order they
    appear, deduplicated; `()` if no '### Evidence' section or no
    recognizable rendered lines are found."""
    section = _done_report_section_lines(body)
    if section is None:
        return ()
    ids: list[str] = []
    in_evidence = False
    for line in section:
        stripped = line.strip()
        if stripped.startswith("### "):
            in_evidence = stripped == "### Evidence"
            continue
        if not in_evidence:
            continue
        match = _EVIDENCE_LINE_RE.match(stripped)
        if match and match.group(1) not in ids:
            ids.append(match.group(1))
    return tuple(ids)


# frob:ticket T-0357
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport.test_recovers_ids_when_structured_evidence_empty  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestReplayEvidenceFromDoneReport.test_noop_when_evidence_already_present  # noqa: E501
def replay_evidence_from_done_report(
    root: Path, ticket_id: str
) -> Result[Ticket, TicketError]:
    """Recover `ticket_id`'s structured `evidence:` field from its own
    committed Done report prose when the field is empty (T-0357): the
    coordinator-land bug where evidence recorded via `frob ticket evidence`
    in a worktree never made it into main's ledger in a form `frob ticket
    close` recognizes (a hand `git merge --no-ff` that bypassed the T-0176/
    T-0479 ledger splice, or a splice that otherwise dropped the field
    while the Done report text survived). Best-effort and idempotent: a
    ticket that already carries structured evidence is returned unchanged
    (`Ok`, no write); a ticket with no evidence and no recognizable
    rendered ids in its Done report returns `Err(MissingEvidence)`
    unchanged -- there is nothing to replay. Recovered ids are NOT
    re-validated against a fresh pytest collection or pass/fail run (no
    such oracle is available here, and re-validating would defeat the
    point of a same-repo-state recovery); callers that need that guarantee
    should follow up with `frob check`'s COV003/TEST001 gates, which
    re-verify independently."""
    with ledger_lock(root):
        loaded = _load_one(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket = loaded.danger_ok
        if ticket.evidence:
            return Ok(ticket)
        recovered = _parse_evidence_ids_from_done_report(ticket.body)
        if not recovered:
            _log.warning(
                "tickets: %s has no structured evidence and no recoverable "
                "ids in its Done report -- nothing to replay",
                ticket_id,
            )
            return Err(TicketError.MissingEvidence)
        updated = ticket.model_copy(update={"evidence": recovered})
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.warning(
        "tickets: %s replayed %d evidence id(s) from its Done report text "
        "(structured evidence: field was empty) -- %s",
        ticket_id,
        len(recovered),
        list(recovered),
    )
    return Ok(updated)


# frob:ticket T-0887
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_ticket_runner_done_report.py::TestBaseRefResolvable.test_unresolvable_ref_in_a_real_repo_is_false  # noqa: E501
# frob:tests tests/test_ticket_runner_done_report.py::TestBaseRefResolvable.test_resolvable_ref_is_true  # noqa: E501
# frob:tests tests/test_ticket_runner_done_report.py::TestBaseRefResolvable.test_non_git_root_is_none  # noqa: E501
def base_ref_resolvable(root: Path, base_ref: str) -> bool | None:
    """Bounded (`run_argv`'s own timeout, never unbounded) check of whether
    `base_ref` resolves to a real commit in `root`'s clone, via `git
    rev-parse --verify --quiet <base_ref>^{commit}` -- the fail-fast guard
    `set_done_report` runs before any other work (T-0887: a typo'd or
    unfetched base ref used to be discovered only indirectly, minutes
    later, via a silently-empty `git diff --stat` or a downstream `frob
    check --ticket` spawn, rather than on the ref itself in seconds).

    Returns `True`/`False` when `root` is a real git checkout (ref
    resolves or does not); returns `None` when `root` itself is not a git
    checkout at all (git's own `not a git repository` exit code, 128) --
    that is a DIFFERENT failure than an unresolvable ref, and callers
    must treat it as "unknown", never as "unresolvable", to preserve the
    pre-T-0887 best-effort behavior for non-git roots (`compute_changed_
    lines`'s own long-standing contract, and every existing `set_done_
    report` caller in the test suite that passes a bare `tmp_path` with
    no git init at all)."""
    from frob.gitio import run_argv

    spawned = run_argv(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "--verify",
            "--quiet",
            f"{base_ref}^{{commit}}",
        ]
    )
    if spawned.is_err:
        return None
    result = spawned.danger_ok
    if result.returncode == 128:
        # Not a git repository at all -- unrelated to the ref itself.
        return None
    return result.returncode == 0


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


_LEADING_DONE_REPORT_HEADING_RE = re.compile(
    r"\A(?:[ \t]*\n)*[ \t]*#{1,6}[ \t]+done report[ \t]*\n?", re.IGNORECASE
)


# frob:ticket T-0826
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_strips_duplicate_leading_heading_from_why  # noqa: E501
def _strip_leading_done_report_heading(why: str) -> str:
    """Strip a leading '## Done report' (any `#` level, any case, optional
    leading blank lines) heading line from `why` (T-0826): `compose_done_
    report` always prepends its own canonical `DONE_REPORT_HEADING`, so a
    caller-supplied `why` (typically `--why-file` content an agent already
    wrote with its own heading) that starts with one too would otherwise
    render TWO headings back to back -- a recurring cosmetic ledger-noise
    finding reviewers kept re-flagging. Only a LEADING heading is
    stripped -- one appearing later in the narrative body is left alone,
    since it is not a duplicate of the one this function's caller is about
    to prepend."""
    return _LEADING_DONE_REPORT_HEADING_RE.sub("", why, count=1)


# frob:ticket T-0458
# frob:ticket T-0826
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_composes_all_three_sections  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestComposeDoneReport.test_strips_duplicate_leading_heading_from_why  # noqa: E501
def compose_done_report(
    why: str,
    changed_lines: Sequence[str],
    evidence: Sequence[str],
    claims: DoneReportClaims | None = None,
) -> str:
    """Compose a full '## Done report' section: the caller's narrative
    `why` plus AUTO-FILLED Changed (`render_changed_block`), Evidence
    (`render_evidence_block`), and (T-0754, when `claims` is given) Captured
    claims (`render_claims_block`) sections -- the mechanical parts are
    always generated, never hand-typed, so they can never drift from what
    frob, git, and a real test/gate run actually observed. `claims=None`
    (the default) omits the Captured claims section entirely, matching
    every caller before T-0754.

    T-0826: if `why` itself already begins with a '## Done report' heading
    (case-insensitive, possibly preceded by blank lines -- e.g. an agent's
    `--why-file` content that already carries its own heading, a recurring
    cosmetic ledger noise reviewers kept flagging), that leading heading
    line is stripped BEFORE composing so the rendered block always has
    exactly one heading, never two."""
    why_text = _strip_leading_done_report_heading(why).strip() or (
        "(no narrative supplied)"
    )
    changed_block = render_changed_block(changed_lines)
    evidence_block = render_evidence_block(evidence)
    claims_section = f"\n\n{render_claims_block(claims)}" if claims is not None else ""
    return (
        f"{DONE_REPORT_HEADING}\n\n"
        f"{why_text}\n\n"
        f"### Changed\n{changed_block}\n\n"
        f"### Evidence\n{evidence_block}{claims_section}\n"
    )


# frob:ticket T-0976
def _capture_done_report_claims(
    ticket_id: str,
    ticket: Ticket,
    run_tests: Callable[[Sequence[str]], int] | None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None,
) -> "DoneReportClaims | None":
    """`set_done_report`'s T-0754/T-0832/T-0846 Captured-claims computation,
    split from its load-compose-write body: `None` unless BOTH `run_tests`
    and `check_gates` were supplied, else a `DoneReportClaims` with gate
    counts recorded as unmeasured (`None`, never a `-1` sentinel, T-0832)
    when `check_gates()` itself returns `None`."""
    if run_tests is None or check_gates is None:
        return None
    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    gate_result = check_gates()
    if gate_result is None:
        # T-0832: never embed a -1 sentinel -- record the gate half of the
        # claim as explicitly unmeasured instead.
        _log.warning(
            "ticket %s: fresh `frob check --ticket %s` produced no "
            "parsable gate-summary -- recording the Captured "
            "claims gate-state as unmeasured (the test-count claim "
            "is unaffected)",
            ticket_id,
            ticket_id,
        )
        gate_errors = gate_warnings = gate_waived = None
    else:
        gate_errors, gate_warnings, gate_waived = gate_result
    error_findings = check_gate_findings() if check_gate_findings is not None else None
    return DoneReportClaims(
        test_count=run_tests(non_cmd),
        evidence_count=len(non_cmd),
        gate_errors=gate_errors,
        gate_warnings=gate_warnings,
        gate_waived=gate_waived,
        error_findings=error_findings,
    )


# frob:ticket T-0458
# frob:ticket T-0754
# frob:ticket T-0832
# frob:ticket T-0846
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_composes_and_writes_atomically  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestSetDoneReport.test_caller_never_touches_markdown  # noqa: E501
# frob:tests tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims.test_claims_captured_from_real_callables  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_two_unmeasured_gate_claims_never_vacuously_match kind="integration"  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity kind="integration"  # noqa: E501
# frob:waive AFFECT001 reason="T-0976 pure internal refactor: extraction of _capture_done_report_claims from this already-documented function, no external contract/behavior change, doc anchor(s) remain accurate as-is"  # noqa: E501
def set_done_report(
    root: Path,
    ticket_id: str,
    *,
    why: str,
    base_ref: str = "main",
    run_tests: Callable[[Sequence[str]], int] | None = None,
    check_gates: Callable[[], tuple[int, int, int] | None] | None = None,
    check_gate_findings: Callable[[], frozenset[tuple[str, str]] | None] | None = None,
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

    T-0754: when BOTH `run_tests` and `check_gates` are supplied, this also
    CAPTURES (never lets the caller type) a `### Captured claims` section:
    `run_tests(non_cmd_evidence_ids)` actually runs the ticket's own
    recorded non-cmd evidence and returns the real passing count, and
    `check_gates()` runs a fresh `frob check --ticket` and returns its
    `(errors, warnings, waived)` COUNTS -- deliberately not that run's
    free-text summary line, whose per-gate timing blob is nondeterministic
    even against an unchanged tree (T-0754 review round 2's FATAL fix) --
    both rendered via `render_claims_block` into the same Done report
    `set_done_report` already writes, and later re-verified against the
    post-merge tree by `frob.tickets._land`'s
    `_reverify_done_report_claims_post_merge` (T-0754's land-side half).
    Either or both omitted (the default, `None`) skips the Captured claims
    section entirely -- unchanged behavior for every caller before T-0754,
    since computing either needs `frob.testing`/`frob.gates`/subprocess
    access `frob.tickets` deliberately does not have (docs/rework.md
    cycle-avoidance); the `frob ticket done-report` CLI supplies both by
    default (see `ticket_runner.py`'s `_done_report`).

    T-0832: `check_gates()` returning `None` means the fresh `frob check
    --ticket` it ran produced no parsable gate-summary (no lease, a crash,
    unparsable output) -- this is recorded as an UNMEASURED gate-state
    claim (`DoneReportClaims.gate_errors=None`, etc.), logged as a
    warning, and rendered via the explicit `unmeasured` marker
    (`render_claims_block`), never as a `-1` sentinel. A `-1` sentinel
    written here previously could later compare equal to another `-1`
    land observed post-merge, passing a re-verification that had actually
    measured nothing on either side (the T-0830 incident). The test-count
    half of the claim is unaffected -- `run_tests` always returns a real
    measured count whenever it runs at all.

    T-0846: `check_gate_findings()` (opt-in, additional to `check_gates`)
    returns a `frozenset[(rule_id, file)]` of the SAME fresh check's error
    findings -- captured alongside the plain count so `land`'s
    re-verification can compare identities (rule id + file) rather than a
    scope-wide total. A count-only comparison let a land whose own diff
    introduced N new errors sail through whenever an unrelated fix on the
    same branch removed more than N (a self-introduced regression
    laundered by a net-better total) -- the gap the count-only T-0846 `>`
    fix left open. `check_gate_findings=None` (the default) records no
    identity set (`DoneReportClaims.error_findings=None`), matching every
    caller before this addition; `_reverify_done_report_claims_post_merge`
    falls back to the count-only comparison whenever either side of the
    claim lacks an identity set.

    T-0887: `base_ref` is validated (`base_ref_resolvable`) BEFORE any
    other work -- an unresolvable ref (in a real git checkout) returns
    `Err(TicketError.BaseRefUnresolvable)` immediately rather than being
    discovered minutes later via a silently-empty diff or a downstream
    `frob check` spawn. T-0887 also moves the (potentially slow, up to
    two 600s `frob check --ticket` subprocess spawns via `check_gates`/
    `check_gate_findings`) claims capture OUTSIDE the `ledger_lock` --
    those are read-only and do not need the single-writer lock at all;
    holding the lock across them used to serialize every OTHER concurrent
    ticket mutation on this ledger behind up to ~20 minutes of subprocess
    spawns (the observed "hangs under concurrent tickets.md lock
    contention" symptom class). Only the final load-compose-write is now
    held under `ledger_lock` end to end, so a concurrent `set_done_
    report`/`add_evidence`/`new_ticket` call on the same ledger still can
    never interleave with THAT part (T-0458 single-writer invariant) --
    the narrow tradeoff is that `ticket.evidence` used to compute the
    non-cmd id list fed to `run_tests`/claims is read once, before the
    lock, and could in principle be stale if evidence changes
    concurrently between that read and the final write; the Evidence
    section itself is always rendered from the freshly-reloaded ticket
    inside the lock, so the written report's Evidence block can never be
    stale, only (rarely) the Captured claims' `evidence_count`."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)

    resolvable = base_ref_resolvable(root, base_ref)
    if resolvable is False:
        _log.error(
            "ticket %s: done-report --base-ref %r does not resolve to a "
            "commit in this clone -- fetch it or pass a base ref that "
            "exists",
            ticket_id,
            base_ref,
        )
        return Err(TicketError.BaseRefUnresolvable)

    preloaded = _load_one(root, ticket_id)
    if preloaded.is_err:
        return Err(preloaded.danger_err)
    changed_lines = compute_changed_lines(root, base_ref)
    claims = _capture_done_report_claims(
        ticket_id, preloaded.danger_ok, run_tests, check_gates, check_gate_findings
    )

    with ledger_lock(root):
        loaded = _load_one(root, ticket_id)
        if loaded.is_err:
            return Err(loaded.danger_err)
        ticket = loaded.danger_ok
        report = compose_done_report(why, changed_lines, ticket.evidence, claims)
        updated = ticket.model_copy(
            update={"body": replace_done_report_section(ticket.body, report)}
        )
        write_result = write_ticket(root, updated)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s Done report set (%d evidence id(s), %d changed line(s)%s)",
        ticket_id,
        len(ticket.evidence),
        len(changed_lines),
        f", claims={claims.test_count}/{claims.evidence_count} tests"
        if claims is not None
        else "",
    )
    return Ok(updated)


# frob:doc docs/modules/tickets.md#public-api
def record_failure(
    root: Path, ticket_id: str, entry: FailureEntry
) -> Result[Ticket, TicketError]:
    """Append entry to the '## Failure log' body section, creating it if absent."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
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


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_unresolvable_commit_rejected  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_short_sha_normalized_to_full_sha  # noqa: E501
def _resolve_review_commit(root: Path, commit: str) -> Result[str, TicketError]:
    """Resolve `commit` (a short SHA, ref name, `HEAD`, ...) to its full
    40-char SHA via `git rev-parse` under `root` (T-0571 review round 2):
    `record_review` must NEVER store a caller-supplied commit verbatim --
    `has_approved_review_for_commit` does a plain string-equality
    comparison against a full `rev-parse HEAD` sha, so an abbreviated
    value (e.g. copied from `git log --oneline`) would silently never
    match and make `close --strict` permanently unsatisfiable for that
    review. `Err(ReviewCommitUnresolvable)` on any git failure (unknown
    ref, not a git repo, ...) -- an unresolvable input is never stored
    raw."""
    from frob.gitio import run_argv

    resolved = run_argv(["git", "-C", str(root), "rev-parse", commit])
    if (
        resolved.is_err
        or resolved.danger_ok.returncode != 0
        or not resolved.danger_ok.stdout.strip()
    ):
        _log.warning(
            "tickets: review --commit %r did not resolve under %s", commit, root
        )
        return Err(TicketError.ReviewCommitUnresolvable)
    return Ok(resolved.danger_ok.stdout.strip())


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#structured-review-channel-t-0571
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_appends_approve_entry  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_blank_findings_rejected  # noqa: E501
# frob:tests tests/test_tickets_review.py::TestRecordReview.test_multiple_reviews_append_only  # noqa: E501
def record_review(
    root: Path,
    ticket_id: str,
    *,
    verdict: ReviewVerdict,
    reviewer: str,
    findings: str,
    commit: str,
) -> Result[Ticket, TicketError]:
    """Append a structured `ReviewEntry` to `ticket_id`'s append-only
    `reviews` list (T-0571) -- the first-class evidence channel for
    adversarial review, replacing a verdict pasted only into dispatch
    chat. `Err(ReviewFindingsMissing)` if `findings` is blank: a review
    record with no findings text is indistinguishable from one nobody
    actually read. `commit` is normalized to its full SHA via
    `_resolve_review_commit` before storage (T-0571 review round 2):
    `Err(ReviewCommitUnresolvable)` if it does not resolve, rather than
    storing an abbreviated/unnormalized value that could never satisfy
    `close --strict`'s exact-match comparison later. Never validates
    `verdict` against the ticket's own state beyond schema -- `close
    --strict` is what decides whether a given review record actually
    satisfies the gate."""
    if not findings.strip():
        return Err(TicketError.ReviewFindingsMissing)
    resolved_commit = _resolve_review_commit(root, commit)
    if resolved_commit.is_err:
        return Err(resolved_commit.danger_err)
    commit = resolved_commit.danger_ok
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    entry = ReviewEntry(
        verdict=verdict,
        reviewer=reviewer,
        findings=findings.strip(),
        commit=commit,
        at=date.today(),
    )
    updated = ticket.model_copy(update={"reviews": ticket.reviews + (entry,)})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    _log.info(
        "tickets: %s recorded review verdict=%s reviewer=%s commit=%s",
        ticket_id,
        verdict.value,
        reviewer,
        commit,
    )
    return Ok(updated)


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_review.py::TestHasApprovedReviewForCommit.test_true_only_for_matching_approve  # noqa: E501
def has_approved_review_for_commit(ticket: Ticket, commit: str) -> bool:
    """Whether `ticket` carries at least one `verdict: approve` review
    record naming exactly `commit` (T-0571) -- the predicate `close
    --strict` gates on. A ticket with zero review records, or reviews that
    only name earlier commits (the code moved since the last review), both
    return `False`: a stale approval is not an approval of the CURRENT
    final commit."""
    return any(
        r.verdict == ReviewVerdict.APPROVE and r.commit == commit
        for r in ticket.reviews
    )


# frob:ticket T-0579
# frob:doc docs/modules/tickets.md#public-api
def drop_ticket(
    root: Path, ticket_id: str, reason: str, *, absorbed_by: str | None = None
) -> Result[Ticket, TicketError]:
    """First-class `frob ticket drop` (T-0579): append a dated reason line
    under '## Drop reason' (creating the section if absent, same pattern as
    `record_failure`'s '## Failure log'), then transition to DROPPED through
    the normal state machine so a held worktree lease is released the same
    way any other terminal transition releases one
    (`_sync_cross_worktree_lease`) -- this replaces the pre-T-0579 workflow
    of hand-editing `state: dropped` directly, which left leases dangling
    and never recorded why. `Err(DropReasonMissing)` if `reason` is blank:
    a drop with no reason is indistinguishable from a silent discard later.
    `absorbed_by` (a ticket id) is appended parenthetically to the line when
    given, but is NOT validated against the queue -- it is a cross-reference
    note, not a `blocked_by`-style edge."""
    if not reason.strip():
        return Err(TicketError.DropReasonMissing)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    loaded = _load_one(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok

    line = f"- {date.today().isoformat()}: {reason.strip()}"
    if absorbed_by:
        line += f" (absorbed by {absorbed_by})"
    new_body = _append_to_section(ticket.body, _DROP_REASON_HEADING, line)
    updated = ticket.model_copy(update={"body": new_body})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)

    transitioned = transition(root, ticket_id, TicketState.DROPPED)
    if transitioned.is_err:
        _log.error(
            "tickets: %s drop reason recorded but transition failed: %s",
            ticket_id,
            transitioned.danger_err,
        )
        return Err(transitioned.danger_err)
    _log.info("tickets: %s dropped: %s", ticket_id, reason.strip())
    return transitioned


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
    "AcceptanceCriterion",
    "Attachment",
    "AttachError",
    "AttachmentSource",
    "BOARD_STATES",
    "BoardColumn",
    "ClipboardError",
    "DoneReportClaims",
    "EpicRollup",
    "FailureEntry",
    "LandError",
    "LandReport",
    "Origin",
    "PRIORITY_RANK",
    "Priority",
    "ReviewEntry",
    "ReviewVerdict",
    "ScopeChangeEntry",
    "ScopeChangeOp",
    "SprintReport",
    "Ticket",
    "TicketError",
    "TicketKind",
    "TicketQueue",
    "TicketSpec",
    "TicketState",
    "TicketTier",
    "add_cmd_evidence",
    "add_evidence",
    "archive",
    "attach",
    "base_ref_resolvable",
    "clipboard_has_image",
    "compose_done_report",
    "compute_changed_lines",
    "dispatch_stale_hours",
    "display_state",
    "doable",
    "doable_blocked",
    "drop_ticket",
    "has_approved_review_for_commit",
    "has_live_lease",
    "is_cmd_evidence",
    "land",
    "large_glob_warnings",
    "leased_by",
    "ledger_lock",
    "load_active",
    "load_queue",
    "load_require_review_for_close",
    "mutate_labels",
    "mutate_scope",
    "set_component",
    "set_kind",
    "set_priority",
    "set_sprint",
    "sprint_view",
    "Stride",
    "board_view",
    "brief_ticket",
    "epic_rollup",
    "migrate",
    "new_ticket",
    "renumber",
    "record_failure",
    "record_review",
    "reconcile",
    "ReconcileReport",
    "parse_claims_from_done_report",
    "render_changed_block",
    "render_claims_block",
    "render_evidence_block",
    "reverify_cmd_evidence",
    "run_cmd_evidence",
    "scope_breadth_context",
    "scope_matches",
    "scope_overlap_globs",
    "set_done_report",
    "splice_ledger",
    "transition",
    "unbound_acceptance",
    "undispatched_stale",
    "validate_evidence",
    "LeaseError",
    "is_lease_ttl_expired",
    "lease_age_seconds",
    "leases_dir",
    "read_all_leases",
    "resolve_lease",
    "sweep_worktrees",
    "ConfirmatoryFinding",
    "MutationEvidenceError",
    "check_ticket_mutation_evidence",
    "agent_env_exports",
]

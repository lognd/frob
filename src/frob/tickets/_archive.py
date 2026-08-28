"""
frob.tickets._archive -- active/archive ledger load and the tickets-archive.md move
(T-1103 split residue of frob.tickets.__init__: the load_active/load_queue/migrate/
archive family, carved out verbatim with its T-0633/T-0764/T-0843/T-0889 lock and
live-lease-refusal directives intact).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._leases import read_all_leases
from frob.tickets._models import (
    RESTORE_LOG_HEADING,
    Ticket,
    TicketError,
    TicketQueue,
    TicketState,
)
from frob.tickets._store import (
    _parse_ticket_file,
    _store_mode,
    git_mv_dir,
    ledger_digest,
    ledger_lock,
    ledger_path,
    load_all,
    load_archive,
    migrate_to_ledger,
    ticket_lock,
    v2_archive_dir,
    v2_ticket_dir,
    write_all,
    write_archive,
    write_ticket,
)
from frob.tickets._worktree_guard import enforce_worktree_lease

# T-1103: shared "frob.tickets" logger name kept explicit (not get_logger(__name__),
# which would read "frob.tickets._archive") -- several tests filter caplog records
# by the package's own logger name, the same monkeypatch/logger-name hazard T-1089's
# ticket_runner split report documented for this family of split.
_log = get_logger("frob.tickets")


# frob:doc docs/modules/tickets.md#public-api
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
# frob:tests tests/test_tickets.py::TestQueue.test_malformed_frontmatter_is_err
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
# frob:ticket T-1437
# frob:tests tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew.test_concurrent_new_ticket_survives_a_racing_archive  # noqa: E501
# frob:tests tests/test_tickets.py::TestArchive.test_id_present_in_both_active_and_archive_collapses_not_refuses  # noqa: E501
# frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_refuses_when_a_live_lease_exists  # noqa: E501
# frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_force_overrides_the_live_lease_refusal  # noqa: E501
# frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_ignores_a_stale_lease_from_a_removed_worktree  # noqa: E501
# frob:tests tests/test_tickets.py::TestArchiveRefusesDuringInFlightWork.test_archive_ignores_a_live_lease_for_a_ticket_it_would_not_touch  # noqa: E501
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
def archive(root: Path, *, force: bool = False) -> Result[int, TicketError]:
    """Move every done/dropped ticket from the active store into
    tickets-archive.md, verbatim (same section format, still tracked and
    greppable); the active ledger keeps only open work. Idempotent -- a
    second call with nothing newly done/dropped moves nothing and returns
    Ok(0). An id already present in BOTH the active store and the archive
    (T-1437's recovery path -- see `_write_archived_and_active`) is
    collapsed to the archive's existing copy and dropped from the active
    ledger, rather than refusing the whole call with `DuplicateId`.
    Returns the number of tickets newly moved (the collapsed-duplicate
    count is not included). See the comment block directly above this
    function for the full T-0633/T-0764/T-0843 locking and
    live-lease-refusal rationale.

    T-1256: a v2-mode repo (`_store_mode(root) == "v2"`) dispatches to
    `archive_v2` instead -- design section 4.3's plain `git mv
    tickets/T-#### tickets/archive/T-####` per ticket, in place of this
    function's whole-ledger read-modify-write of two monofiles. Checked
    FIRST, before `enforce_worktree_lease` even runs, since `archive_v2`
    does its own lease check (mirroring `renumber_one`'s T-1255
    dispatch)."""
    if _store_mode(root) == "v2":
        return archive_v2(root, force=force)
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
            worktree_guard = _refuse_archive_if_other_worktrees_live(root)
            if worktree_guard.is_err:
                return Err(worktree_guard.danger_err)
            guard = _refuse_archive_if_leased(root, to_archive)
            if guard.is_err:
                return Err(guard.danger_err)

        return _write_archived_and_active(root, active, to_archive, active_digest)


# frob:ticket T-1750
# frob:doc docs/modules/tickets-data-storage.md#archive-the-live-worktree-guard-t-1750
# frob:tests tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees.test_refuses_when_another_worktree_exists kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees.test_force_overrides_the_live_worktree_refusal kind="unit"  # noqa: E501
# frob:tests tests/test_tickets_organization.py::TestArchiveRefusesLiveWorktrees.test_no_other_worktree_archives_normally kind="unit"  # noqa: E501
# frob:waive COV007 reason="docs/modules/tickets-data-storage.md's Archive: the \
# live-worktree guard (T-1750) section documents several symbols under one section, \
# not just a public entry point -- the many-symbols- one-section convention this repo \
# already accepted for vet.md (T-2810 declined to touch it), not a T-2810-shaped \
# duplicate"
def _refuse_archive_if_other_worktrees_live(root: Path) -> Result[None, TicketError]:
    """`archive`'s T-1750 in-flight-worktree guard: `Err
    (ArchiveLiveLeaseExists)` if ANY OTHER linked git worktree of `root`'s
    repository currently exists, else `Ok(None)`.

    This is a DIFFERENT, broader precondition than `_refuse_archive_if_
    leased` (T-0843/T-0976): that check only refuses when a ticket THIS
    call would move holds a live lease, on the theory that archiving
    unrelated closed work is safe even mid-drive. The 2026-08-07 incident
    this ticket fixes showed that theory is not enough on its own -- a
    live worktree with an UNRELATED in-progress ticket still has its OWN
    checkout of the active ledger, and archiving on `main` while it is
    live invites the exact ledger-drift-on-merge risk `docs/modules/
    tickets.md`'s own "archive in a quiet window" guidance has always
    named in prose but never enforced. This function is that
    enforcement: a live worktree existing AT ALL (not just one holding a
    lease archive would touch) refuses the call, naming every worktree
    path found, with `force=True` (`--force`) as the documented override
    for an operator who has confirmed it is safe (e.g. every live
    worktree's ticket work is already landed and only the worktree
    directory itself has not been cleaned up yet).

    Reuses `frob.tickets._reconcile._live_worktrees` (the same `git
    worktree list --porcelain` primitive `frob ticket reconcile` already
    uses to find orphan worktrees) rather than re-deriving a second git-
    worktree-listing implementation -- late-imported to avoid a module-
    level import cycle (`_reconcile` imports from `_archive`'s sibling
    modules, not this one directly, but keeping the cross-family import
    local matches this package's existing late-import convention for
    cross-family calls, e.g. `frob.tickets._doable`'s own late imports)."""
    from frob.tickets._reconcile import _live_worktrees

    live = _live_worktrees(root)
    if not live:
        return Ok(None)
    _log.error(
        "tickets: archive refused -- %d live git worktree(s) exist "
        "besides the primary checkout (%s); archiving now risks the "
        "T-1750 ledger-drift-on-merge incident (a worktree's own "
        "pre-archive ledger view diverging from main's post-archive "
        "state) -- run in a quiet window (no live worktrees) or pass "
        "--force",
        len(live),
        ", ".join(str(p) for p in live),
    )
    return Err(TicketError.ArchiveLiveLeaseExists)


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


# frob:ticket T-1256
# frob:ticket T-1750
# frob:doc docs/design/ledger-v2.md#43-archive-as-git-mv
# frob:tests tests/test_ticket_land.py::TestArchiveV2.test_archive_moves_directory_via_git_mv_no_content_rewrite  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestArchiveV2.test_archive_v2_regression_two_sided_divergence_no_clobber  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestArchiveV2.test_archived_v2_ticket_still_resolves_as_blocker  # noqa: E501
# frob:waive AFFECT001 reason="T-1750 only extracts the existing git-mv-per-ticket \
# loop into a private helper (_archive_v2_move_tickets, ARCH001 line-budget fix) -- \
# design/ledger-v2.md#43-archive-as-git-mv describes the git-mv-per-ticket design \
# decision, which is unchanged; nothing new to document at that anchor"
def archive_v2(root: Path, *, force: bool = False) -> Result[int, TicketError]:
    """v2-mode `archive` (design section 4.3): `git mv tickets/T-####
    tickets/archive/T-####` per done/dropped ticket, zero content rewrite --
    no `ticket.md`/`done-report.md` byte changes, so there is no destination
    FILE being rewritten for two divergent branches' archive sweeps to
    clobber (the T-0959 failure mode structurally impossible here, not
    merely guarded). Idempotent, same contract as `archive`: nothing
    done/dropped and still active returns `Ok(0)`.

    Each move is taken under that ticket's own `ticket_lock` (design
    section 3), not a single whole-tree lock -- concurrent archives of
    DIFFERENT tickets never contend, and a `git mv` of one ticket's
    directory can never race a write to another ticket's directory.

    T-1750: deliberately does NOT get the broader `_refuse_archive_if_
    other_worktrees_live` guard `archive` (the v1 monofile path) gets --
    a `git mv` per ticket directory is a real rename between two disjoint
    git paths, which a concurrent worktree's `git merge` resolves
    correctly with no custom splice code (`TestArchiveV2.test_archive_v2_
    regression_two_sided_divergence_no_clobber` reproduces the exact
    two-sided-divergence shape unforced, with a live sibling worktree
    throughout, and passes) -- the T-1750 incident's actual failure mode
    (two divergent rewrites of the SAME `tickets.md`/`tickets-archive.md`
    monofile pair) cannot occur on this path."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
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
        _log.info("tickets: archive_v2 -- nothing to move")
        return Ok(0)

    if not force:
        guard = _refuse_archive_if_leased(root, to_archive)
        if guard.is_err:
            return Err(guard.danger_err)

    return _archive_v2_move_tickets(root, to_archive)


# frob:ticket T-2954
# frob:waive DUP001 reason="the flagged matches are unrelated validation functions \
# across unrelated modules (invariants.py, _elaborate.py, _accept.py, _land_merge.py) \
# that only share the generic 'check a condition, return Err on failure' Result shape \
# every guard function in this codebase has -- not the same rule, no shared behavior \
# to extract"
def _refuse_non_terminal_archive_target(
    ticket_id: str, ticket: Ticket
) -> Result[None, TicketError]:
    """`_archive_v2_move_tickets`'s defense-in-depth guard, split out
    under ARCH001's per-body budget: `Err(ArchiveNonTerminalTicket)` if
    `ticket`'s state is not terminal (done/dropped), else `Ok(None)`. See
    `_archive_v2_move_tickets`'s own docstring for the full T-2954
    rationale (structurally unreachable via the normal selection filter
    today, defense-in-depth against a future weakening of it)."""
    if ticket.state not in (TicketState.DONE, TicketState.DROPPED):
        _log.error(
            "tickets: archive_v2 REFUSED to move %s -- state=%s is "
            "not terminal (done/dropped); archive only ever moves "
            "CLOSED work into tickets/archive/ (T-2954: this is the "
            "exact invariant violation T-0450's incident produced -- "
            "refusing here rather than reproducing it)",
            ticket_id,
            ticket.state.value,
        )
        return Err(TicketError.ArchiveNonTerminalTicket)
    return Ok(None)


# frob:ticket T-1750
# frob:ticket T-2954
def _archive_v2_move_tickets(
    root: Path, to_archive: dict[str, Ticket]
) -> Result[int, TicketError]:
    """`archive_v2`'s per-ticket `git mv` loop, split out to stay under
    ARCH001's per-body budget (T-1750): each ticket id's directory move
    runs under its own `ticket_lock`, so concurrent archives of DIFFERENT
    tickets never contend.

    T-2954: `archive_v2`'s own `to_archive` dict-comprehension already
    filters to done/dropped only, so a non-terminal ticket cannot reach
    this loop TODAY -- but that filter is the only thing standing between
    "archive only ever moves closed work" and T-0450's own incident (a
    `queued` ticket stranded under `tickets/archive/`, root cause never
    conclusively identified, T-2954's own investigation only ruled OUT
    the two archive entry points as the direct cause). A second, cheap
    defense-in-depth check (`_refuse_non_terminal_archive_target`) right
    here -- at the one place that actually performs the `git mv` --
    refuses loudly (`Err(ArchiveNonTerminalTicket)`) rather than silently
    reproducing the exact stranding this ticket's series exists to close,
    if a future refactor of the filter above (or a new caller of this
    function) ever weakens it."""
    moved = 0
    for ticket_id in sorted(to_archive):
        guard = _refuse_non_terminal_archive_target(ticket_id, to_archive[ticket_id])
        if guard.is_err:
            return Err(guard.danger_err)
        with ticket_lock(root, ticket_id):
            old_dir = v2_ticket_dir(root, ticket_id)
            if not old_dir.is_dir():
                _log.debug(
                    "tickets: archive_v2 skipping %s -- already moved "
                    "(concurrent archive won the race)",
                    ticket_id,
                )
                continue
            new_dir = v2_archive_dir(root, ticket_id)
            if new_dir.exists():
                _log.error(
                    "tickets: archive_v2: %s already exists at destination %s",
                    ticket_id,
                    new_dir,
                )
                return Err(TicketError.DuplicateId)
            move_result = git_mv_dir(root, old_dir, new_dir)
            if move_result.is_err:
                return Err(move_result.danger_err)
            rewrite_result = _rewrite_moved_attachment_paths(
                new_dir, ticket_id, to_archive[ticket_id]
            )
            if rewrite_result.is_err:
                return Err(rewrite_result.danger_err)
            moved += 1

    _log.info("tickets: archived %d ticket(s) (v2, git mv)", moved)
    return Ok(moved)


# frob:ticket T-2986
def _rewrite_moved_attachment_paths(
    new_dir: Path, ticket_id: str, ticket: Ticket
) -> Result[None, TicketError]:
    """After `git_mv_dir` has relocated `ticket_id`'s directory to
    `new_dir` (`tickets/archive/<id>/`), rewrite any `attachments[].path`
    entry in the just-moved `ticket.md` that is still v2-self-contained-
    shaped (`_record_attachment`'s convention: `<id>/attachments/NN-x.ext`,
    relative to `tickets_dir(root)`) so it reads `archive/<id>/
    attachments/NN-x.ext` instead -- COV004 (`src/frob/gates/__init__.py`)
    resolves every attachment as the fixed `Path("tickets") /
    attachment.path`, so a path left pointing at the pre-move location
    silently stops resolving the moment `git mv` relocates the file out
    from under it (T-2986: the root cause of 10 archived-ticket COV004
    findings on main, `chore(tickets): archive 886 ticket(s)`).

    A plain text substitution on the moved `ticket.md`, not a re-
    serialize through `write_ticket` -- `write_ticket`'s v2 path resolves
    `ticket_id`'s directory via `v2_ticket_dir` (always the ACTIVE
    location), so writing through it here would recreate `tickets/<id>/`
    at the very path `git_mv_dir` just vacated. A legacy-shared-dir
    attachment path (`attachments/<id>/...`, predating the v2 self-
    contained layout, never itself moved by archive) is left untouched by
    the `f"{ticket_id}/"`-prefix match -- only the id-prefixed v2 shape
    this archive call could have broken is rewritten. No-op (`Ok(None)`,
    no write) when `ticket` has no attachment in that shape, so a ticket
    with zero or only-legacy attachments never takes an unnecessary
    write."""
    prefix = f"{ticket_id}/"
    if not any(a.path.startswith(prefix) for a in ticket.attachments):
        return Ok(None)
    ticket_md = new_dir / "ticket.md"
    try:
        text = ticket_md.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error(
            "tickets: archive_v2: failed to read moved %s for attachment "
            "path rewrite: %s",
            ticket_md,
            exc,
        )
        return Err(TicketError.WriteFailed)
    rewritten = re.sub(
        rf"^(- path: ){re.escape(ticket_id)}/",
        rf"\1archive/{ticket_id}/",
        text,
        flags=re.M,
    )
    if rewritten == text:
        _log.warning(
            "tickets: archive_v2: %s attachments claimed id-prefixed paths "
            "but no line matched the rewrite pattern in %s -- leaving as is",
            ticket_id,
            ticket_md,
        )
        return Ok(None)
    try:
        ticket_md.write_text(rewritten, encoding="utf-8")
    except OSError as exc:
        _log.error(
            "tickets: archive_v2: failed to write rewritten %s: %s", ticket_md, exc
        )
        return Err(TicketError.WriteFailed)
    _log.info(
        "tickets: archive_v2: rewrote attachment path(s) for %s to archive/ "
        "prefix (T-2986)",
        ticket_id,
    )
    return Ok(None)


# frob:ticket T-0889
# frob:ticket T-1437
# frob:tests tests/test_tickets.py::TestArchive.test_id_present_in_both_active_and_archive_collapses_not_refuses  # noqa: E501
def _write_archived_and_active(
    root: Path,
    active: dict[str, Ticket],
    to_archive: dict[str, Ticket],
    active_digest: str | None,
) -> Result[int, TicketError]:
    """Merge `to_archive` into the archive file and drop it from the active
    ledger, in that order.

    T-1437: an id already present in the archive is no longer a hard
    `Err(DuplicateId)` refusal -- it is dropped from `to_archive` (the
    archive's own existing copy wins, unconditionally, never overwritten)
    and still removed from the active ledger, so `archive` COLLAPSES the
    duplicate instead of refusing outright. This is the recovery path the
    T-1437 incident needed: a `git merge main`-triggered ledger-driver
    resurrection (fixed at its own root cause by
    `frob.app.ticket_runner._archived_ids_for_merge_driver`, T-1437) could
    still leave a worktree's `tickets.md` carrying an id its own
    `tickets-archive.md` ALSO carries (e.g. from a stale merge that ran
    before this fix, or a hand-edited ledger) -- before this change,
    `archive` on such a worktree refused outright with `DuplicateId` and
    offered no CLI path to repair; a duplicate id is now a self-healing
    no-op for that id (already archived, nothing further to do) rather
    than a hard stop for the WHOLE `archive` call. Returns the count of
    ids genuinely NEWLY archived (the overlap set does not count, since
    nothing new was written for it) -- callers already treat `Ok(0)` as
    "nothing to move" (see this function's own docstring precedent on
    `archive`).

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
        _log.warning(
            "tickets: archive collapsing %d id(s) already present in "
            "tickets-archive.md -- archive copy wins, active copy dropped "
            "(no re-archive): %s",
            len(overlap),
            sorted(overlap),
        )
    newly_archived = {tid: t for tid, t in to_archive.items() if tid not in overlap}

    if newly_archived:
        archive_write = write_archive(root, {**archived, **newly_archived})
        if archive_write.is_err:
            return Err(archive_write.danger_err)

    keep = {tid: t for tid, t in active.items() if tid not in to_archive}
    active_write = write_all(root, keep, expected_digest=active_digest)
    if active_write.is_err:
        return Err(active_write.danger_err)

    _log.info(
        "tickets: archived %d ticket(s) (%d already-archived duplicate(s) collapsed)",
        len(newly_archived),
        len(overlap),
    )
    return Ok(len(newly_archived))


# frob:ticket T-2954
# frob:doc docs/modules/tickets-lifecycle.md#frob-ticket-restore-t-2954
# frob:tests \
# tests/unit/test_ticket_restore.py::TestRestore.test_restores_a_non_terminal_archived_\
# ticket_to_active
# frob:tests \
# tests/unit/test_ticket_restore.py::TestRestore.test_refuses_when_not_archived
# frob:tests \
# tests/unit/test_ticket_restore.py::TestRestore.test_refuses_when_destination_already_\
# exists
# frob:tests tests/unit/test_ticket_restore.py::TestRestore.test_refuses_a_blank_reason
def restore(root: Path, ticket_id: str, *, reason: str) -> Result[Ticket, TicketError]:
    """`frob ticket restore <id> --reason TEXT` (T-2954): the missing
    repair primitive for a ticket stranded under `tickets/archive/` in a
    NON-terminal state -- `archive`/`archive_v2` only ever SELECT
    done/dropped tickets to move (see `to_archive`'s state filter in both
    functions above), so they cannot themselves put a ticket into this
    state; the incident this closes (T-0450: `state: queued` sitting
    under `tickets/archive/T-0450/`, 37 days stale) happened by some
    OTHER means this repo's own house rules already forbid (a hand edit
    of the ledger) -- but once it happens, nothing could move the ticket
    back: `frob ticket drop <id>` resolves ids via the active store only
    (`_load_one`/`load_all`, never the archive), so it reports plain
    `NotFound` against an archived id, and no un-archive verb existed at
    all.

    `git mv tickets/archive/<id> tickets/<id>` -- the exact reverse of
    `_archive_v2_move_tickets`'s own move, including the reverse of its
    T-2986 attachment-path rewrite (an archived ticket's v2-self-
    contained attachment paths read `archive/<id>/attachments/...`;
    restored, they must read `<id>/attachments/...` again, or COV004
    stops resolving them the moment they are back in the active tree).
    Then appends a dated `## Restore log` entry (mirrors `reopen_ticket`'s
    own `## Reopen log` accountability pattern) recording WHY -- a ledger
    correction this consequential is never silent, matching `reopen`'s
    own `--reason`-required precedent (`Err(RestoreReasonMissing)` on a
    blank one).

    Deliberately does NOT touch `ticket.state` -- unlike `reopen_ticket`
    (which repairs a specific done->queued transition), `restore` repairs
    a LOCATION invariant (active vs. archived), not a state one; whatever
    non-terminal state the stranded ticket already carries (T-0450's own
    `queued`) is exactly right for it to land back in the active store
    with no further correction needed. A restored ticket that happens to
    be done/dropped (an operator restoring by hand for some other reason,
    e.g. inspecting/editing it) is left exactly that way too -- the next
    `frob ticket archive` run picks it back up naturally, same as any
    other done/dropped ticket, no special-casing required here.

    v2-mode only (`Err(RestoreV1Unsupported)` otherwise) -- the v1
    monofile backend's `tickets-archive.md`/`tickets.md` splice is a
    different, more involved primitive (`_write_archived_and_active`'s
    reverse) this ticket's scope did not extend to; T-0450's own repo
    runs v2 (design section 7's fresh-repo default), the only backend
    this incident is actually reproducing against.

    Validation-and-dispatch only (ARCH001 split): the actual git-mv +
    rewrite + body-write sequence is `_restore_v2`."""
    if not reason.strip():
        return Err(TicketError.RestoreReasonMissing)
    if _store_mode(root) != "v2":
        _log.error(
            "tickets: restore refused -- %s is not in v2 (file-per-ticket) "
            "mode, and restore has no v1 (monofile) implementation",
            root,
        )
        return Err(TicketError.RestoreV1Unsupported)
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    return _restore_v2(root, ticket_id, reason=reason)


# frob:ticket T-2954
def _restore_v2(
    root: Path, ticket_id: str, *, reason: str
) -> Result[Ticket, TicketError]:
    """`restore`'s actual git-mv + attachment-path-reverse + `## Restore
    log` write, split out under ARCH001's per-body budget -- see
    `restore`'s own docstring for the full rationale."""
    with ticket_lock(root, ticket_id):
        archive_dir = v2_archive_dir(root, ticket_id)
        if not archive_dir.is_dir():
            _log.error(
                "tickets: restore refused -- %s has no directory under "
                "tickets/archive/ (nothing to restore)",
                ticket_id,
            )
            return Err(TicketError.RestoreNotArchived)
        active_dir = v2_ticket_dir(root, ticket_id)
        if active_dir.exists():
            _log.error(
                "tickets: restore refused -- %s already exists at the "
                "active destination %s",
                ticket_id,
                active_dir,
            )
            return Err(TicketError.RestoreDestinationExists)
        move_result = git_mv_dir(root, archive_dir, active_dir)
        if move_result.is_err:
            return Err(move_result.danger_err)
        rewrite_result = _rewrite_restored_attachment_paths(active_dir, ticket_id)
        if rewrite_result.is_err:
            return Err(rewrite_result.danger_err)
        loaded = _parse_ticket_file(active_dir / "ticket.md")
        if loaded.is_err:
            _log.error(
                "tickets: restore: %s moved to %s but failed to re-parse "
                "afterward (%s) -- inspect by hand",
                ticket_id,
                active_dir,
                loaded.danger_err,
            )
            return Err(loaded.danger_err)
        ticket = loaded.danger_ok
        from frob.tickets._reporting import _append_to_section
        from frob.tickets._store import sanitize_narrative_for_ledger

        line = (
            f"- {date.today().isoformat()}: "
            f"{sanitize_narrative_for_ledger(reason.strip())}"
        )
        new_body = _append_to_section(ticket.body, RESTORE_LOG_HEADING, line)
        restored = ticket.model_copy(update={"body": new_body})
        write_result = write_ticket(root, restored)
        if write_result.is_err:
            return Err(write_result.danger_err)
    _log.info(
        "tickets: %s restored (tickets/archive/%s -> tickets/%s, state=%s "
        "unchanged): %s",
        ticket_id,
        ticket_id,
        ticket_id,
        restored.state.value,
        reason.strip(),
    )
    return Ok(restored)


# frob:ticket T-2954
def _rewrite_restored_attachment_paths(
    new_dir: Path, ticket_id: str
) -> Result[None, TicketError]:
    """`restore`'s reverse of `_rewrite_moved_attachment_paths` (T-2986):
    after `git_mv_dir` has relocated `ticket_id`'s directory back to
    `new_dir` (active `tickets/<id>/`), rewrite any `attachments[].path`
    entry still reading the archive-prefixed `archive/<id>/attachments/
    NN-x.ext` shape back to the plain `<id>/attachments/NN-x.ext` form --
    the exact inverse substitution, same no-op-when-nothing-matches
    posture."""
    ticket_md = new_dir / "ticket.md"
    try:
        text = ticket_md.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error(
            "tickets: restore: failed to read moved %s for attachment "
            "path rewrite: %s",
            ticket_md,
            exc,
        )
        return Err(TicketError.WriteFailed)
    rewritten = re.sub(
        rf"^(- path: )archive/{re.escape(ticket_id)}/",
        rf"\1{ticket_id}/",
        text,
        flags=re.M,
    )
    if rewritten == text:
        return Ok(None)
    try:
        ticket_md.write_text(rewritten, encoding="utf-8")
    except OSError as exc:
        _log.error(
            "tickets: restore: failed to write rewritten %s: %s", ticket_md, exc
        )
        return Err(TicketError.WriteFailed)
    _log.info(
        "tickets: restore: rewrote attachment path(s) for %s back to the "
        "active prefix (T-2954)",
        ticket_id,
    )
    return Ok(None)

"""frob.tickets._scope -- the scope-mutation family (T-1123, T-1108/T-1103
residue): `mutate_scope` and everything it leans on (lease-conflict
detection for an `--add`, the T-0561 new-concrete-file carve-out, the
evidence-orphan guard for a `--remove`, the over-broad-glob nudge, and the
audit-trail `ScopeChangeEntry` builder), split out of `frob.tickets.__init__`
following T-1103/T-1108's per-family extraction pattern (smallest cohesive
unit first, public surface re-exported via `__all__`, zero caller-visible
behavior change, `frob:tests`/`frob:doc` edges moved verbatim with the
functions they annotate).

Kept together because every function here ultimately serves ONE call:
`mutate_scope`'s own validate-then-write pipeline for `frob ticket scope
--add/--remove`. `_load_ticket_and_queue` (the merged active+archive
load+lookup `mutate_scope` needs) intentionally STAYS in `frob.tickets.
__init__` -- it is also `set_priority`/`set_kind`/`set_tier`/`set_sprint`'s
own shared load helper, not scope-specific -- so `mutate_scope` late-imports
it from the package at call time rather than at load time, the same
load-order-safe indirection T-1103/T-1108 used for `renumber_one`/
`doable`'s own forward references, since `__init__` imports THIS module
before `_load_ticket_and_queue` exists yet at its own module scope.
"""

from __future__ import annotations

import fnmatch
import getpass
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from typani.result import Err, Ok, Result

if TYPE_CHECKING:
    from frob.tickets._leases import _LeaseRecord

from frob.excludes import is_test_file
from frob.logging import get_logger
from frob.tickets._doable import _over_broad_scope_entries, scope_breadth_context
from frob.tickets._models import (
    ScopeChangeEntry,
    ScopeChangeOp,
    Ticket,
    TicketError,
    TicketState,
    _glob_is_subset,
    scope_overlap_globs,
)
from frob.tickets._models import _split_scope_entries as _normalize_scope_entries
from frob.tickets._store import ledger_lock, write_ticket
from frob.tickets._worktree_guard import enforce_worktree_lease

_log = get_logger("frob.tickets")


def _current_actor() -> str:
    """Best-effort identity for a `scope_changes` audit entry's `actor` field
    -- the OS login name, or `"unknown"` if the platform/sandbox refuses to
    report one (never raises)."""
    try:
        return getpass.getuser()
    except OSError:
        return "unknown"
    except Exception:
        # "never raises" (this function's own docstring) covers any
        # platform/sandbox surprise, not just `OSError` (EXHAUST001,
        # T-1371).
        return "unknown"


# frob:ticket T-0455
# frob:ticket T-0561
# frob:ticket T-0422
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
    subset check above.

    T-1868: `queue` alone is NOT sufficient -- it reflects a sibling
    worktree's `start` only once THIS worktree has merged that commit in,
    which let two in-progress tickets in different worktrees hold the
    identical path simultaneously (the confirmed T-1868 incident). When
    `root` is given, `_scope_add_live_lease_conflict` (see its own
    docstring for the full mechanism) additionally checks every other
    ticket's LIVE cross-worktree lease, which needs no merge to be
    current."""
    if any(_glob_is_subset(glob, existing) for existing in own_scope):
        return None
    new_file = root is not None and _is_new_concrete_file_glob(glob, root)
    queue_conflict = _scope_add_queue_conflict(
        glob, ticket_id, queue, root=root, new_file=new_file
    )
    if queue_conflict is not None and root is not None:
        # frob:ticket T-2095
        # The queue-based check reflects THIS worktree's own possibly-
        # stale local ledger copy of the holder's ticket -- a narrowing
        # the holder published to the live cross-worktree lease side-
        # channel (`mutate_scope` -> `record_lease`, T-0473/T-1993) is
        # invisible to it until a merge/land. Before trusting a stale
        # conflict, check the SAME holder's live lease record (if any):
        # if it exists and no longer overlaps `glob`, the holder has
        # already released this path and the queue-based finding is
        # superseded, so fall through to the fresher live-lease check
        # instead of returning the stale result directly. This can only
        # ever CLEAR a conflict the queue-based check found, never invent
        # one -- narrowing is monotone-safe (T-2095's own acceptance
        # criterion 3); a holder with no live lease recorded at all keeps
        # the pre-existing queue-based answer unchanged.
        if not _live_lease_still_conflicts(queue_conflict[0], glob, root):
            queue_conflict = None
    if queue_conflict is not None:
        return queue_conflict
    if root is not None:
        return _scope_add_live_lease_conflict(
            glob, ticket_id, root, queue, new_file=new_file
        )
    return None


# frob:ticket T-2095
def _live_lease_still_conflicts(holder_id: str, glob: str, root: Path) -> bool:
    """`True` unless `holder_id` has a LIVE cross-worktree lease
    (`read_all_leases`, T-0473) recorded and that lease's CURRENT scope no
    longer overlaps `glob` (T-2095) -- the narrow, monotone-safe check
    `_scope_add_conflicts` uses to decide whether a stale queue-based
    conflict against `holder_id` has been superseded by a narrowing the
    holder already published to the shared side-channel.

    Deliberately conservative in every direction that is NOT "the holder
    has since released this exact path": no recorded lease at all for
    `holder_id` (never started in this process's view of the side-channel,
    or the side-channel itself is unavailable) returns `True` (keep
    trusting the queue-based conflict -- there is no fresher signal to
    prefer it over), and a lease whose scope STILL overlaps `glob` also
    returns `True` (nothing has changed; the conflict is real). Only a
    lease that demonstrably no longer covers `glob` returns `False`, which
    is what makes this safe to use as a pre-check ahead of the existing,
    independently-conflict-detecting `_scope_add_live_lease_conflict` --
    it never widens what counts as a conflict, only narrows a stale one
    away when the live record proves it has already been released."""
    from frob.tickets._leases import read_all_leases

    lease = next(
        (entry for entry in read_all_leases(root) if entry.ticket_id == holder_id),
        None,
    )
    if lease is None:
        return True
    return scope_overlap_globs((glob,), lease.scope) is not None


# frob:ticket T-1880
# frob:doc docs/modules/tickets.md#public-api
# frob:tests \
# tests/test_tickets_scope_mutation.py::TestScopeLeaseConflict.test_no_collision_is_none
# frob:tests tests/test_tickets_scope_mutation.py::TestScopeLeaseConflict.test_first_colliding_entry_wins  # noqa: E501
def scope_lease_conflict(
    ticket_id: str,
    scope: Sequence[str],
    queue: dict[str, Ticket],
    own_scope: Sequence[str] = (),
    *,
    root: Path | None = None,
) -> tuple[str, str] | None:
    """`(holding_ticket_id, holder_glob)` for the FIRST entry of `scope`
    that overlaps another in-progress ticket's lease (queue-based or, when
    `root` is given, live cross-worktree -- `_scope_add_conflicts`'s own
    T-0453/T-0561/T-1868 mechanism), or `None` if every entry is free.

    THE single "does this scope collide with an already-in-progress
    ticket's lease" entrypoint (T-1880): `mutate_scope`'s `--add` validation
    and `frob ticket start`'s own grant-time refusal
    (`frob.app.ticket_runner._lifecycle._refuse_on_scope_lease_collision`)
    both call this instead of each running its own loop over
    `_scope_add_conflicts` -- T-1880's own incident was exactly two call
    sites answering "does this collide?" differently: `--add` refused a
    scope WIDENED after start (T-1868), but nothing checked a collision
    already present in a ticket's ORIGINAL FILED scope at `start` time
    (confirmed: T-1851/T-1870 both held `src/frob/app/config.py`
    simultaneously this exact way). One home, so the two paths cannot
    diverge again.

    `own_scope` is `mutate_scope`'s T-0485 "already grandfathered" subset
    exemption -- pass the ticket's OWN pre-mutation scope for an `--add`
    call, or leave it `()` for a grant-time check (`start`) where there is
    no pre-existing granted subset to exempt against."""
    for glob in scope:
        conflict = _scope_add_conflicts(glob, ticket_id, queue, own_scope, root=root)
        if conflict is not None:
            return conflict
    return None


# frob:ticket T-1868
def _scope_add_queue_conflict(
    glob: str,
    ticket_id: str,
    queue: dict[str, Ticket],
    *,
    root: Path | None,
    new_file: bool,
) -> tuple[str, str] | None:
    """`_scope_add_conflicts`'s pre-T-1868 queue-based loop (T-0455/T-0561/
    T-1356), split out unchanged (ARCH001: `_scope_add_conflicts` grew past
    the line threshold once the T-1868 live-lease half was added) -- every
    OTHER in-progress ticket in `queue` whose declared scope overlaps
    `glob`, with T-1356's same-worktree exemption and T-0561's new-file
    carve-out both applied exactly as before."""
    for holder in sorted(queue.values(), key=lambda t: t.id):
        if holder.id == ticket_id or holder.state is not TicketState.IN_PROGRESS:
            continue
        collision = scope_overlap_globs((glob,), holder.scope)
        if collision is None:
            continue
        if root is not None and _same_worktree_lease(root, ticket_id, holder.id):
            _log.info(
                "tickets: %s --add %r exempted from %s's lease on %r "
                "(T-1356: both tickets are leased to the same worktree "
                "-- one agent, not a real cross-agent collision)",
                ticket_id,
                glob,
                holder.id,
                collision[1],
            )
            continue
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


# frob:ticket T-1868
# frob:ticket T-1909
# frob:doc docs/modules/tickets-lifecycle.md#cross-worktree-lease-side-channel-t-0473
# frob:tests \
# tests/test_ticket_leases_cross_worktree.py::TestScopeAddRefusesLiveCrossWorktreeLease.test_scope_add_refused_by_unmerged_sibling_worktrees_live_lease  # noqa: E501
# frob:tests \
# tests/test_ticket_leases_cross_worktree.py::TestScopeAddIgnoresTerminalLease.test_dropped_ticket_on_local_ledger_does_not_block_live_lease  # noqa: E501
def _scope_add_live_lease_conflict(
    glob: str,
    ticket_id: str,
    root: Path,
    queue: dict[str, Ticket],
    *,
    new_file: bool,
) -> tuple[str, str] | None:
    """T-1868: the cross-worktree-lease-side-channel half of
    `_scope_add_conflicts` -- checks `glob` against every OTHER ticket's
    LIVE lease (`read_all_leases`), not just what this worktree's local
    ticket ledger happens to already know about. Dead-worktree leases are
    already excluded by `read_all_leases` itself (`_probe_worktree_
    liveness`); expired-TTL leases are filtered here explicitly
    (`is_lease_ttl_expired`), the same way `_refuse_if_foreign_live_lease`
    checks it -- `read_all_leases` only prunes a lease whose WORKTREE has
    vanished, not one whose TTL has simply lapsed. Matches `_refuse_if_
    foreign_live_lease`'s own posture: a lease with no live holder behind
    it is not a real collision. `_same_worktree_lease`'s T-1356 exemption
    and T-0561's new-file carve-out both still apply here, mirroring the
    queue-based check exactly so a live-lease conflict is never STRICTER
    than a queue-based one for the same underlying holder -- only able to
    catch a REAL conflict the queue-based check's merge-dependent
    staleness missed.

    T-1909: a lease file on the shared side-channel is written once, when
    its ticket enters `IN_PROGRESS`, and only ever removed by THAT SAME
    worktree's own subsequent `frob.tickets.transition` call (`release_
    lease`) -- a worktree abandoned (never removed, never run again) after
    its ticket was dropped/closed FROM A DIFFERENT worktree (the common
    coordinator-driven drop/close path) leaves a lease file that
    `read_all_leases` has no way to know is now stale, since the file's
    own worktree path still exists on disk and its TTL has not
    necessarily lapsed. `queue` -- `root`'s own authoritative, just-
    merged-with-main ledger view, already threaded in from `_scope_add_
    conflicts`/`scope_lease_conflict`'s caller -- is checked here exactly
    like `_scope_add_queue_conflict`'s own `holder.state is not TicketState.
    IN_PROGRESS` skip and `frob.tickets._doable._cross_worktree_leases`'s
    existing DONE/DROPPED filter: if `root`'s ledger already knows this
    lease's ticket is DONE or DROPPED, the lease is dead regardless of
    what the stale worktree's own unreachable local copy still says."""
    from frob.tickets._leases import is_lease_ttl_expired, read_all_leases

    for lease in read_all_leases(root):
        if lease.ticket_id == ticket_id or is_lease_ttl_expired(lease):
            continue
        collision = scope_overlap_globs((glob,), lease.scope)
        if collision is None:
            continue
        if _live_lease_collision_is_exempt(
            glob, ticket_id, root, queue, lease, collision, new_file=new_file
        ):
            continue
        _log.warning(
            "tickets: %s --add %r caught by %s's LIVE cross-worktree lease "
            "on %r -- this worktree's local ticket ledger has not merged "
            "that start/scope-add yet (T-1868)",
            ticket_id,
            glob,
            lease.ticket_id,
            collision[1],
        )
        return (lease.ticket_id, collision[1])
    return None


# frob:ticket T-1909
def _live_lease_collision_is_exempt(
    glob: str,
    ticket_id: str,
    root: Path,
    queue: dict[str, Ticket],
    lease: _LeaseRecord,
    collision: tuple[str, str],
    *,
    new_file: bool,
) -> bool:
    """`_scope_add_live_lease_conflict`'s per-lease exemption check (ARCH001
    split: the T-1909 terminal-ledger-state check pushed the loop body past
    the line threshold) -- `True` iff `lease`'s collision with `glob` is
    one of the three known-safe shapes: T-1909 (`lease.ticket_id` is
    DONE/DROPPED on `root`'s OWN ledger -- the lease is stale, left behind
    by a worktree abandoned after its ticket was finished/dropped some
    OTHER way), T-1356 (`ticket_id` and `lease.ticket_id` are leased to the
    SAME worktree), or T-0561 (a new, not-yet-existing concrete file whose
    collision is not an exact match of the holder's own glob). Each branch
    logs its own reason at INFO before returning `True`, matching this
    function's pre-split call sites exactly."""
    local = queue.get(lease.ticket_id)
    if local is not None and local.state in (TicketState.DONE, TicketState.DROPPED):
        _log.info(
            "tickets: %s --add %r ignored %s's live lease on %r "
            "(T-1909: %s is %s on this ledger -- the lease is stale, "
            "left behind by an abandoned worktree)",
            ticket_id,
            glob,
            lease.ticket_id,
            collision[1],
            lease.ticket_id,
            local.state,
        )
        return True
    if _same_worktree_lease(root, ticket_id, lease.ticket_id):
        _log.info(
            "tickets: %s --add %r exempted from %s's live lease on %r "
            "(T-1356: both tickets are leased to the same worktree)",
            ticket_id,
            glob,
            lease.ticket_id,
            collision[1],
        )
        return True
    if new_file and collision[1] != glob:
        _log.info(
            "tickets: %s --add %r exempted from %s's live lease on %r "
            "(T-0561: new file, holder glob is not an exact match)",
            ticket_id,
            glob,
            lease.ticket_id,
            collision[1],
        )
        return True
    return False


# frob:ticket T-1356
# frob:ticket T-1883
def _same_worktree_lease(root: Path, requesting_id: str, holder_id: str) -> bool:
    """Thin re-export of `frob.tickets._leases.same_worktree_lease` (T-1883:
    the shared conflict predicate now lives there, called from both this
    module's `--add` collision check and `_doable.leased_by`'s
    `doable --show-blocked` collision check -- see that function's own
    docstring for the WHY). Kept as a local name so this module's existing
    call sites (`_scope_add_queue_conflict`, `_scope_add_live_lease_conflict`)
    do not need their own call-site edits."""
    from frob.tickets._leases import same_worktree_lease

    return same_worktree_lease(root, requesting_id, holder_id)


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


def _evidence_paths_needing(glob: str, ticket: Ticket) -> tuple[str, ...]:
    """Every evidence id's leading `path::` segment that `glob` covers
    (T-1356: split out of `_scope_remove_orphans_evidence` so the
    remaining-coverage check below can reuse the same "covered by glob"
    test without duplicating the `path::`-split logic)."""
    return tuple(
        path
        for entry in ticket.evidence
        for path in (entry.split("::", 1)[0],)
        if fnmatch.fnmatch(path, glob)
    )


# frob:ticket T-0455
# frob:ticket T-1356
def _scope_remove_orphans_evidence(
    glob: str, ticket: Ticket, remaining_scope: Sequence[str] = ()
) -> bool:
    """Whether removing `glob` from `ticket.scope` would orphan already-
    recorded evidence (T-0455 guardrail).

    T-1356: the check that actually matters is whether evidence stays
    COVERED after the removal, not whether `glob` itself happened to be
    one of the globs covering it -- the pre-T-1356 behavior refused ANY
    removal of a glob that covers evidence, even when `remaining_scope`
    (the ticket's OTHER, still-declared globs) would keep covering that
    same evidence on its own, producing an unresolvable deadlock with
    `_scope_add_conflicts`'s own lease refusal (a real incident: `tests/
    unit/**` could not be narrowed to release a path a sibling ticket
    needed, because a duplicate/broader glob would have kept it covered
    regardless). `remaining_scope=()` (the default, matching every
    pre-T-1356 caller) preserves the exact prior strict behavior."""
    needed = _evidence_paths_needing(glob, ticket)
    if not needed:
        return False
    if not remaining_scope:
        return True
    return any(
        not any(fnmatch.fnmatch(path, other) for other in remaining_scope)
        for path in needed
    )


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
    # T-1356: the FINAL scope this call would leave behind, if every
    # requested `remove` glob is accepted -- what actually matters for
    # "does evidence stay covered", not scope-minus-one-glob-at-a-time.
    # T-1944: `evidence_scope` is unioned in -- it also covers evidence
    # (D-02, `evidence_covers_scope`) without ever being a `--remove`
    # target itself (this function only ever operates on `scope` globs),
    # so it always survives into `remaining_scope` and can keep evidence
    # covered on its own.
    remaining_scope = tuple(g for g in ticket.scope if g not in remove_globs) + tuple(
        ticket.evidence_scope
    )
    for glob in remove_globs:
        if glob not in ticket.scope:
            _log.error(
                "tickets: %s cannot remove %r, not in declared scope %s",
                ticket_id,
                glob,
                ticket.scope,
            )
            return Err(TicketError.ScopeRemoveNotDeclared)
        if _scope_remove_orphans_evidence(glob, ticket, remaining_scope):
            _log.error(
                "tickets: %s cannot remove %r, covers recorded evidence not "
                "kept covered by the remaining scope %s",
                ticket_id,
                glob,
                remaining_scope,
            )
            return Err(TicketError.ScopeRemoveOrphansEvidence)
    conflict = scope_lease_conflict(
        ticket_id, add_globs, queue, ticket.scope, root=root
    )
    if conflict is not None:
        holder_id, holder_glob = conflict
        _log.error(
            "tickets: %s cannot lease an add glob: held by in-progress %s (scope %r)",
            ticket_id,
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
# frob:tests \
# tests/test_tickets_scope_mutation.py::TestMutateScope.test_add_free_path_granted
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

    T-1123: `_load_ticket_and_queue` (the merged active+archive load+lookup
    this needs) is late-imported from the PACKAGE here, not called as a
    module-local name -- `frob.tickets.__init__` imports THIS module before
    `_load_ticket_and_queue` exists at its own module scope yet (it stays
    defined in `__init__` itself, shared with `set_priority`/`set_kind`/
    `set_tier`/`set_sprint`), the same load-order-safe indirection T-1103/
    T-1108 established for `renumber_one`/`doable`'s own forward references.
    """
    from frob.tickets import _load_ticket_and_queue

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
    # frob:ticket T-1993
    # The cross-worktree lease's recorded scope must never drift from the
    # ledger's once an in-progress ticket's scope changes -- otherwise
    # another worktree's `doable` would keep colliding against (or missing)
    # a stale scope forever.
    if updated.state is TicketState.IN_PROGRESS:
        from frob.tickets._leases import record_lease

        record_lease(
            root,
            ticket_id,
            _lease_scope_to_record(
                root, ticket_id, updated.scope, add_globs, remove_globs
            ),
        )
    _log.info(
        "tickets: %s scope changed (+%d/-%d): %s",
        ticket_id,
        len(add_globs),
        len(remove_globs),
        reason,
    )
    return Ok(updated)


# frob:ticket T-1993
def _lease_scope_to_record(
    root: Path,
    ticket_id: str,
    updated_scope: tuple[str, ...],
    add_globs: tuple[str, ...],
    remove_globs: tuple[str, ...],
) -> tuple[str, ...]:
    """What to write into `ticket_id`'s cross-worktree lease record after a
    scope mutation (T-1993) -- NOT simply `updated_scope` (the caller's own
    freshly-written ledger scope), because `updated_scope` was computed from
    THIS worktree's own on-disk copy of `tickets/<id>/ticket.md`, which can
    be stale relative to `main` (a worktree that never merged a sibling's
    narrowing commit still carries the old, broader scope in its own
    checkout). Blindly re-recording `updated_scope` is exactly the T-1993
    incident: worktree B, still on the pre-narrowing ledger snapshot,
    computed its OWN `updated_scope` as a superset of what worktree A had
    already narrowed the SHARED lease to, and overwrote A's correct,
    narrower lease with that superset purely by writing last.

    Instead, this applies the SAME `add`/`remove` delta `mutate_scope` (or
    `demote_to_evidence_only`) just validated and wrote to the ledger --
    but onto whatever scope is CURRENTLY recorded in the shared lease file
    (`read_all_leases`), not onto this worktree's possibly-stale ledger
    snapshot. A worktree that is fully up to date computes the identical
    result either way (its local scope and the recorded lease scope already
    agree), so this changes nothing for the common case; a stale worktree's
    legitimate delta (e.g. adding a path nobody has touched) now lands on
    top of the shared lease's true current state instead of reverting it.
    Falls back to `updated_scope` when no lease is recorded yet for this
    ticket (first `IN_PROGRESS` entry -- nothing to reconcile against) or
    when the lease cannot be read at all (best-effort side channel, same
    posture as `record_lease` itself).

    This does NOT make the lease authoritative over the ledger: the ledger
    write (`updated_scope`, `_write_scope_mutation`) already happened and is
    unaffected by this function -- only the DERIVED side-channel mirror is
    reconciled differently, against its own prior state rather than a
    snapshot that may already be behind it."""
    from frob.tickets._leases import read_all_leases

    try:
        existing = next(
            (lease for lease in read_all_leases(root) if lease.ticket_id == ticket_id),
            None,
        )
    except Exception:
        # read_all_leases is itself best-effort over a peer-writable side
        # channel; any surprise here falls back to the pre-T-1993 behavior
        # rather than blocking the scope mutation that already succeeded.
        return updated_scope
    if existing is None:
        return updated_scope
    base = tuple(g for g in existing.scope if g not in remove_globs)
    for glob in add_globs:
        if glob not in base:
            base += (glob,)
    return base


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


# frob:ticket T-1944
# frob:doc docs/modules/tickets-landing.md#evidence-only-scope-t-1944
# frob:tests \
# tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly.test_demote_\
# releases_the_lease_and_keeps_evidence_covered
# frob:tests \
# tests/unit/test_tickets_evidence_only_scope.py::TestDemoteToEvidenceOnly.test_demote_\
# refuses_an_undeclared_glob
def demote_to_evidence_only(
    root: Path, ticket_id: str, globs: Sequence[str], *, reason: str
) -> Result[Ticket, TicketError]:
    """Migrate one or more of `ticket_id`'s EXISTING `scope` entries into
    `evidence_scope` (T-1944) -- the remedy for a ticket already stuck
    the old way, holding a write lease it never uses purely because an
    earlier `scope --add` was the only way to satisfy D-02 for a pre-
    existing test cited as evidence (the confirmed T-1686 incident: an
    epic with zero lines of code changed, unable to release a lease on
    the repo's highest-traffic test file, because `scope --remove` on it
    correctly refused via `ScopeRemoveOrphansEvidence`).

    Deliberately NOT built on `mutate_scope`'s `remove`/`add` pair -- a
    plain `--remove glob --add glob` round-trip would hit the exact
    `ScopeRemoveOrphansEvidence` deadlock this function exists to escape
    (removing `glob` from `scope` orphans evidence UNTIL the same atomic
    write also adds it to `evidence_scope`, and `_validate_scope_
    mutation` has no way to see that pairing). This performs both halves
    of that move in ONE write instead: `glob` leaves `scope` and joins
    `evidence_scope` atomically, so evidence coverage (D-02) is NEVER
    momentarily false. Does not touch `ScopeRemoveOrphansEvidence` itself
    -- a genuine `scope --remove` with no matching demotion still refuses
    exactly as before; this is an ADDITIONAL, narrower move, not a
    weakening of that guard.

    Refuses (`ScopeRemoveNotDeclared`) for any `glob` not currently in
    `ticket.scope` -- the same "must be declared to be removed" rule
    `mutate_scope`'s own remove path enforces, so this can never silently
    invent scope history that never existed. A `glob` already present in
    `evidence_scope` is a no-op for that entry (removed from `scope`,
    stays exactly once in `evidence_scope`, never duplicated)."""
    leased = enforce_worktree_lease(root)
    if leased.is_err:
        return Err(leased.danger_err)
    demote_globs = _normalize_scope_entries(tuple(globs))
    if not demote_globs:
        _log.error("tickets: %s demote-to-evidence-only requires >=1 glob", ticket_id)
        return Err(TicketError.ScopeChangeEmpty)
    if not reason.strip():
        _log.error("tickets: %s demote-to-evidence-only requires --reason", ticket_id)
        return Err(TicketError.ScopeChangeReasonMissing)

    with ledger_lock(root):
        written = _demote_to_evidence_only_locked(root, ticket_id, demote_globs, reason)
        if written.is_err:
            return Err(written.danger_err)
        updated = written.danger_ok
    # frob:ticket T-1993
    if updated.state is TicketState.IN_PROGRESS:
        from frob.tickets._leases import record_lease

        record_lease(
            root,
            ticket_id,
            _lease_scope_to_record(root, ticket_id, updated.scope, (), demote_globs),
        )
    _log.info(
        "tickets: %s demoted %d scope glob(s) to evidence-only (write lease "
        "released, D-02 coverage kept): %s",
        ticket_id,
        len(demote_globs),
        reason,
    )
    return Ok(updated)


# frob:ticket T-1979
def _demote_to_evidence_only_locked(
    root: Path, ticket_id: str, demote_globs: tuple[str, ...], reason: str
) -> Result[Ticket, TicketError]:
    """The load-validate-write half of `demote_to_evidence_only` (T-1979:
    split out to keep the parent under ARCH001's line threshold, zero
    behavior change) -- caller holds `ledger_lock(root)` already."""
    from frob.tickets import _load_ticket_and_queue

    loaded = _load_ticket_and_queue(root, ticket_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket, _queue = loaded.danger_ok

    for glob in demote_globs:
        if glob not in ticket.scope:
            _log.error(
                "tickets: %s cannot demote %r, not in declared scope %s",
                ticket_id,
                glob,
                ticket.scope,
            )
            return Err(TicketError.ScopeRemoveNotDeclared)

    new_scope = tuple(s for s in ticket.scope if s not in demote_globs)
    new_evidence_scope = ticket.evidence_scope + tuple(
        g for g in demote_globs if g not in ticket.evidence_scope
    )
    new_entries = _scope_change_entries((), demote_globs, reason)
    updated = ticket.model_copy(
        update={
            "scope": new_scope,
            "evidence_scope": new_evidence_scope,
            "scope_changes": ticket.scope_changes + new_entries,
        }
    )
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    return Ok(updated)

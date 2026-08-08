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

from typani.result import Err, Ok, Result

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
    if queue_conflict is not None:
        return queue_conflict
    if root is not None:
        return _scope_add_live_lease_conflict(glob, ticket_id, root, new_file=new_file)
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
# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests \
# tests/test_ticket_leases_cross_worktree.py::TestScopeAddRefusesLiveCrossWorktreeLease.test_scope_add_refused_by_unmerged_sibling_worktrees_live_lease  # noqa: E501
def _scope_add_live_lease_conflict(
    glob: str, ticket_id: str, root: Path, *, new_file: bool
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
    staleness missed."""
    from frob.tickets._leases import is_lease_ttl_expired, read_all_leases

    for lease in read_all_leases(root):
        if lease.ticket_id == ticket_id or is_lease_ttl_expired(lease):
            continue
        collision = scope_overlap_globs((glob,), lease.scope)
        if collision is None:
            continue
        if _same_worktree_lease(root, ticket_id, lease.ticket_id):
            _log.info(
                "tickets: %s --add %r exempted from %s's live lease on %r "
                "(T-1356: both tickets are leased to the same worktree)",
                ticket_id,
                glob,
                lease.ticket_id,
                collision[1],
            )
            continue
        if new_file and collision[1] != glob:
            _log.info(
                "tickets: %s --add %r exempted from %s's live lease on %r "
                "(T-0561: new file, holder glob is not an exact match)",
                ticket_id,
                glob,
                lease.ticket_id,
                collision[1],
            )
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


# frob:ticket T-1356
def _same_worktree_lease(root: Path, requesting_id: str, holder_id: str) -> bool:
    """Whether `requesting_id` (the ticket asking for a new `--add` glob,
    running from `root`) and `holder_id` (the ticket whose scope the glob
    would collide with) are BOTH leased to the same worktree (T-1356) --
    the standing-policy series-worktree case where two tickets share one
    agent, not two agents genuinely racing to touch the same files. The
    cross-worktree lease side-channel (`read_all_leases`) is the one place
    that knows which worktree a ticket is actually leased to; a ticket with
    no recorded lease at all (never `frob ticket start`-ed in ANY worktree,
    or a stale/removed lease) never matches, so this can only ever narrow
    an existing conflict, never invent a new exemption out of thin air.

    `root` itself is resolved to its true git worktree top-level
    (`frob.gitio.repo_root`, the same worktree-correct resolution `enforce_
    worktree_lease` uses) rather than compared as a raw path, so a `root`
    passed as a subdirectory of the worktree still matches correctly."""
    from frob.gitio import repo_root
    from frob.tickets._leases import read_all_leases

    resolved_root = repo_root(root)
    if resolved_root.is_err:
        return False
    root_worktree = str(resolved_root.danger_ok.resolve())

    requesting_worktree: str | None = None
    holder_worktree: str | None = None
    for lease in read_all_leases(root):
        if lease.ticket_id == requesting_id:
            requesting_worktree = lease.worktree
        elif lease.ticket_id == holder_id:
            holder_worktree = lease.worktree
    # T-1356: `requesting_id` is the ticket ACTIVELY running this CLI
    # invocation FROM `root` -- if the lease side-channel has no record
    # for it yet (e.g. its very first `scope --add` right after `start`,
    # before any lease-recording write has landed), `root` itself IS its
    # worktree; falling back to `root_worktree` here (rather than treating
    # a missing self-lease as "no match") is what makes that common case
    # work instead of a same-worktree exemption silently never firing on
    # a brand-new ticket.
    if requesting_worktree is None:
        requesting_worktree = root_worktree
    return holder_worktree is not None and requesting_worktree == holder_worktree


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
    remaining_scope = tuple(g for g in ticket.scope if g not in remove_globs)
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

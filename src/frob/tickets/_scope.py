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

# frob:waive INV006 reason="T-1123: exclusivity-vocabulary hits below (only/never) \
# are source-level design-rationale prose describing already-implemented internal \
# behavior (verifiable by reading the code each comment annotates), carried verbatim \
# from tickets/__init__.py's own T-0585 INV006 first-turn-on disposition -- not a \
# separate cross-module contract needing its own tracked invariant"

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

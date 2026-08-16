"""frob.tickets._draft_finalize -- provisional-draft-id finalization
(T-1192).

Split out of `frob.tickets._new_renumber` (T-1192, LARGE001 residue
after T-1074/T-1186/T-1187/T-1188/T-1189, following the same verbatim-
move pattern): `finalize_draft`/`finalize_draft_for_land` (the T-0162/
T-1179 callable finalize step that assigns a draft id its final
sequential `T-####` id and rewrites the ledger plus every code reference
via `renumber_one`) plus their shared private critical-section helper
`_finalize_draft_for_land_locked`. Zero caller-visible behavior change --
every moved function keeps its original body, docstring, and
`frob:ticket`/`frob:tests` directives verbatim; `frob.tickets.__init__`
already imports both public names directly from this new module path
instead of `_new_renumber`.

T-1103's package-level re-import indirection (`from frob.tickets import
renumber_one as _renumber_one`, so a test monkeypatching
`frob.tickets.renumber_one` is still observed) is preserved verbatim --
it was already routed through the package, not the old module-local
name, so moving the caller to a different module changes nothing about
that indirection.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._archive import _load_merged
from frob.tickets._models import Attachment, TicketError
from frob.tickets._new_renumber import _next_ticket_id_shared
from frob.tickets._provisional import is_draft_id
from frob.tickets._store import allocator_lock, ledger_lock, tickets_dir, write_ticket

# T-1103: shared "frob.tickets" logger name kept explicit (not
# get_logger(__name__), which would read "frob.tickets._draft_finalize")
# -- several tests filter caplog records by the package's own logger name,
# the same monkeypatch/logger-name hazard T-1089's ticket_runner split
# report documented for this family of split.
_log = get_logger("frob.tickets")


# frob:ticket T-2199
# frob:tests tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords.test_attachment_path_follows_the_rename  # noqa: E501
# frob:tests tests/unit/test_draft_finalize_attachments.py::TestFinalizeDraftRelocatesAttachmentRecords.test_sha256_is_reverified_at_the_new_location  # noqa: E501
def _relocate_attachment_records(
    root: Path, old_id: str, new_id: str
) -> Result[None, TicketError]:
    """T-2199: `renumber_one`/`renumber_one_v2` moves `old_id`'s directory
    (and any attachment FILES nested under it) to `new_id`'s new v2
    directory, and rewrites every code/ledger prose REFERENCE to the id --
    but never the ticket's own structured `attachments` list, which was
    already written (by an earlier `attach()` call, before this rename)
    with `Attachment.path` values still prefixed by `old_id`. Left alone,
    those records point at a directory that no longer exists (measured on
    T-2195: two attachment records still read `T-draft-0bd874ac/
    attachments/...` after promotion, while the files themselves already
    lived under `T-2195/attachments/`, producing 3 COV004 errors).

    Rewrites each `old_id`-prefixed `Attachment.path` to its `new_id`
    equivalent and RE-VERIFIES the recorded `sha256` against the file at
    that new location -- a move that lost or corrupted a file fails LOUDLY
    here (`Err(TicketError.WriteFailed)`) rather than silently leaving a
    valid-looking but wrong path recorded. This is deliberately a
    structured rewrite of the known `Attachment.path` shape (`<id>/
    attachments/NN-x.ext`), never a lexical/text substitution of the old
    id across the ticket file -- a blind string replace would also hit
    prose that legitimately cites the draft id historically (T-2199's own
    acceptance). A no-op (`Ok(None)`) if `new_id`'s ticket carries no
    attachment recorded under the old prefix."""
    from frob.tickets import _load_one

    loaded = _load_one(root, new_id)
    if loaded.is_err:
        return Err(loaded.danger_err)
    ticket = loaded.danger_ok
    old_prefix = f"{old_id}/"
    if not any(a.path.startswith(old_prefix) for a in ticket.attachments):
        return Ok(None)

    new_attachments: list[Attachment] = []
    for attachment in ticket.attachments:
        if not attachment.path.startswith(old_prefix):
            new_attachments.append(attachment)
            continue
        new_rel_path = f"{new_id}/{attachment.path[len(old_prefix) :]}"
        new_abs_path = tickets_dir(root) / new_rel_path
        if not new_abs_path.exists():
            _log.error(
                "tickets: _relocate_attachment_records: %s -> %s expected "
                "attachment at %s but it does not exist -- file lost "
                "during the rename",
                old_id,
                new_id,
                new_abs_path,
            )
            return Err(TicketError.WriteFailed)
        actual_sha256 = hashlib.sha256(new_abs_path.read_bytes()).hexdigest()
        if actual_sha256 != attachment.sha256:
            _log.error(
                "tickets: _relocate_attachment_records: %s -> %s attachment "
                "%s sha256 mismatch after rename (recorded=%s actual=%s) -- "
                "file corrupted during the move",
                old_id,
                new_id,
                new_abs_path,
                attachment.sha256,
                actual_sha256,
            )
            return Err(TicketError.WriteFailed)
        new_attachments.append(attachment.model_copy(update={"path": new_rel_path}))
        _log.info(
            "tickets: _relocate_attachment_records: %s -> %s relocated "
            "attachment record %s -> %s (sha256 verified)",
            old_id,
            new_id,
            attachment.path,
            new_rel_path,
        )

    updated = ticket.model_copy(update={"attachments": tuple(new_attachments)})
    write_result = write_ticket(root, updated)
    if write_result.is_err:
        return Err(write_result.danger_err)
    return Ok(None)


# frob:ticket T-0162
# frob:ticket T-1090
# frob:ticket T-1669
# frob:doc docs/modules/tickets-lifecycle.md#provisional-ids
# frob:tests tests/test_tickets_ledger_concurrency.py::TestFinalizeDraftAllocationRace.test_two_concurrent_finalize_draft_calls_get_distinct_ids  # noqa: E501
# frob:tests tests/test_tickets_ledger_concurrency.py::TestPromoteVsLandFinalizeAllocationRace.test_promote_and_land_finalize_never_allocate_the_same_id  # noqa: E501
# frob:waive AFFECT001 reason="T-1669 adds an internal lock (allocator_lock) around \
# this function's existing critical section -- the public contract \
# docs/modules/tickets-lifecycle.md#provisional-ids and #public-api describe (assign a \
# draft its final id, atomically, no manual handling) is unchanged; \
# docs/modules/tickets.md is a large repo-wide hub file, out of this ticket's narrowed \
# scope (T-2076 holds a live lease on src/frob/tickets/_land.py, the other file this \
# ticket originally scoped, so scope was narrowed rather than widened into an \
# unrelated hub doc)"
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

    T-1090: the next-id COMPUTATION (`_next_ticket_id` against `_load_merged`'s
    snapshot) used to run entirely OUTSIDE any lock, with `renumber_one`
    acquiring `ledger_lock` only afterward, once `final_id` was already
    fixed. Two concurrent `finalize_draft` calls against the same `root`
    (two sibling lands each renumbering their own residue draft, the T-1086
    vs T-0684 field incident) could both load the same pre-write snapshot,
    both compute the SAME `final_id`, and then serialize only at the
    `renumber_one` write -- the second writer's `_load_and_validate_
    renumber_ids` reload happens under the lock, but if the first writer's
    id happened to land via a DIFFERENT path in between (e.g. a concurrent
    `new_ticket` claiming that exact number first), the second `renumber_one`
    call would silently rename onto a slot a third write had just vacated,
    or a caller retrying after a transient `DuplicateId` could recompute
    from another stale snapshot -- there was no single atomic span covering
    both the read that decides the id and the write that claims it. Now the
    whole read-compute-write sequence is held under ONE `ledger_lock(root)`
    span (reentrant, so `renumber_one`'s own internal lock acquisition below
    is a no-op re-entry in the same thread/process rather than a deadlock),
    mirroring the `new_ticket`/T-0458 pattern and the T-1036 splice-guard
    lineage: allocation and commit are now a single atomic unit under the
    lock, so a concurrent finalizer blocked on the same lock always
    recomputes its own `final_id` against the FRESH post-write ledger once
    it acquires the lock, never a stale pre-write snapshot.

    T-1103: `renumber_one` is re-imported from the PACKAGE at call time
    (rather than called as the module-local name), so a test that
    monkeypatches `frob.tickets.renumber_one` observes `finalize_draft`
    routing through the patched callable too.

    T-1669: the whole critical section is now ALSO held under `root`'s
    `allocator_lock` (T-1253's dedicated id-allocation lock, `.frob/
    tickets-allocator.lock` -- a distinct file from `ledger_lock`'s own
    `.frob/tickets.lock`, defined but never actually wired into any
    allocator until now), wrapping the pre-existing `ledger_lock` span
    rather than replacing it. `ledger_lock(root)` alone only ever
    serialized this function against OTHER callers that also take
    `ledger_lock(root)` -- `finalize_draft_for_land` (the `frob ticket
    land` path) deliberately does NOT take `main_root`'s `ledger_lock`
    (see that function's own docstring for the git-tracked-merge
    collision this avoids), so a `finalize_draft` call here (`frob ticket
    promote`, or Tier-A's `fix_tick002_renumber`) and a concurrent `frob
    ticket land`'s draft finalization could each compute the identical
    `final_id` against the same pre-write snapshot and both "succeed" --
    each writing to a DIFFERENT tree (this call's `root` vs. the land's
    own worktree), so neither write itself ever errors; the collision only
    surfaces later, at squash time, as a forced re-renumber (measured
    twice in one land, T-2060: ids T-2041 and T-2045 each claimed out from
    under it by a concurrent land). `allocator_lock` is the ONE lock both
    `finalize_draft` and `finalize_draft_for_land` now share, so they
    always serialize against each other regardless of which root/worktree
    each one's OWN write lands in.

    T-2122: `allocator_lock(root)` alone was not enough -- it lives at
    `root/.frob/tickets-allocator.lock`, a PER-CHECKOUT path, so two
    DIFFERENT roots (this worktree vs. the primary checkout a `new_ticket`
    call runs against) never actually contended on it, and the id itself
    was still decided by scanning a snapshot that cannot see a sibling
    checkout's not-yet-landed claim. `final_id` now comes from
    `_next_ticket_id_shared` (`frob.tickets._new_renumber`), which reads
    a single counter file shared by every checkout of this repo instead
    of `root`'s own tree -- see that function's docstring for why the
    scan could not be fixed by locking it more tightly."""
    if not is_draft_id(draft_id):
        _log.debug("tickets: finalize_draft(%s): already final, no-op", draft_id)
        return Ok(draft_id)
    with allocator_lock(root), ledger_lock(root):
        merged = _load_merged(root)
        if merged.is_err:
            return Err(merged.danger_err)
        tickets = merged.danger_ok
        if draft_id not in tickets:
            _log.error("tickets: finalize_draft: %s not found", draft_id)
            return Err(TicketError.NotFound)
        final_id = _next_ticket_id_shared(
            root, {tid: t for tid, t in tickets.items() if tid != draft_id}
        )
        from frob.tickets import renumber_one as _renumber_one

        result = _renumber_one(root, draft_id, final_id)
        if result.is_err:
            return Err(result.danger_err)
        relocated = _relocate_attachment_records(root, draft_id, final_id)
        if relocated.is_err:
            return Err(relocated.danger_err)
        _log.info("tickets: finalized draft %s -> %s", draft_id, final_id)
        return Ok(final_id)


# frob:ticket T-1179
# frob:ticket T-1669
# frob:doc docs/modules/tickets-lifecycle.md#provisional-ids
# frob:tests tests/test_tickets_collision.py::TestFinalizeDraftForLandMainFreshCeiling.test_id_ceiling_reads_current_main_not_stale_worktree_view  # noqa: E501
# frob:tests tests/test_tickets_ledger_concurrency.py::TestPromoteVsLandFinalizeAllocationRace.test_promote_and_land_finalize_never_allocate_the_same_id  # noqa: E501
# frob:waive AFFECT001 reason="T-1669 adds allocator_lock around this function's \
# existing critical section -- the public contract \
# docs/modules/tickets-lifecycle.md#provisional-ids describes (finalize a draft's id \
# fresh against main, atomically) is unchanged; docs/modules/tickets.md is out of this \
# ticket's narrowed scope, see finalize_draft's identical waiver above"
def finalize_draft_for_land(
    worktree: Path, draft_id: str, main_root: Path
) -> Result[str, TicketError]:
    """Land-path twin of `finalize_draft` (T-1179 acceptance [0]): same
    rename primitive, but the next-id CEILING is computed from
    `main_root`'s CURRENT on-disk ledger -- read fresh (not from a stale
    in-memory snapshot), unioned with `worktree`'s own view -- instead of
    `worktree`'s (possibly stale) view alone.

    2026-07-29 incident: a ticket filed directly on main (`new_ticket`,
    itself serialized by `ledger_lock(main_root)`) is invisible to a land
    whose worktree was branched/merged before that filing landed. The old
    `finalize_draft(worktree, ...)` computed its id ceiling from
    `worktree`'s copy alone and could re-mint the exact id `new_ticket`
    had just claimed on main; the later squash-splice then silently
    clobbered the main-side block (46a115c4 clobbered by 17c6ca89). This
    reads `main_root`'s ledger fresh from disk (closing the staleness gap
    that caused the incident) WITHOUT holding `main_root`'s own
    `ledger_lock` across the read -- only `worktree`'s lock is held, same
    footprint as plain `finalize_draft`. Locking `main_root` here was
    tried and reverted: it leaves `main_root/.frob/tickets.lock` behind as
    a stray artifact on `root`'s working tree for the remainder of this
    land, and on a repo/fixture where `.frob/` is NOT gitignored (the
    worktree branch legitimately tracks its OWN `.frob/tickets.lock`,
    T-1006) the subsequent squash-merge then refuses with git's own
    "untracked working tree file would be overwritten" error -- a real,
    reproduced regression, not a hypothetical one. The residual race this
    leaves (a `new_ticket` landing on main in the narrow window between
    this unlocked read and the eventual squash-apply) is closed by the
    SECOND guard instead: the squash-time ticket-scoped splice
    (`_overlay_landed_ticket`, acceptance [1]) refuses loudly on any
    id/title mismatch rather than silently overwriting, catching exactly
    this residual window under a REAL lock (`_squash_and_splice_ledger`'s
    own `ledger_lock(root)`) at the point that actually commits to main.

    A no-op (`Ok(draft_id)` unchanged) if `draft_id` is already final,
    mirroring `finalize_draft`.

    T-1669: now also held under `main_root`'s `allocator_lock` (T-1253's
    dedicated id-allocation lock) around the whole critical section --
    deliberately NOT `main_root`'s `ledger_lock`, so the git-tracked-merge
    collision this docstring's prior paragraph documents (a stray `.frob/
    tickets.lock` colliding with a worktree branch's own tracked copy at
    squash time) is not reintroduced: `allocator_lock` lives at its own
    distinct path (`.frob/tickets-allocator.lock`, T-1253), the same
    "give cross-root coordination its own lock file" technique `_land_
    lock` already uses for exactly this reason (see `_land_lock`'s own
    module comment). This closes the real gap the SECOND guard mentioned
    above (the squash-time `_overlay_landed_ticket` mismatch refusal) only
    ever detected AFTER the fact, forcing a manual re-renumber (T-2060: ids
    T-2041/T-2045 each claimed out from under a land by a concurrent
    `frob ticket promote`/Tier-A auto-fix, since `finalize_draft` and this
    function shared no lock at all before T-1669) -- `allocator_lock` now
    makes the two paths queue instead of collide, so the id this function
    computes is never stale by the time it commits."""
    if not is_draft_id(draft_id):
        _log.debug(
            "tickets: finalize_draft_for_land(%s): already final, no-op", draft_id
        )
        return Ok(draft_id)
    main_root = main_root.resolve()
    worktree = worktree.resolve()
    with allocator_lock(main_root), ledger_lock(worktree):
        return _finalize_draft_for_land_locked(worktree, draft_id, main_root)


def _finalize_draft_for_land_locked(
    worktree: Path, draft_id: str, main_root: Path
) -> Result[str, TicketError]:
    """`finalize_draft_for_land`'s critical section, split out to keep the
    public entry point under the ARCH001 line budget -- runs under BOTH
    `main_root`'s and `worktree`'s `ledger_lock` (acquired by the caller)."""
    main_merged = _load_merged(main_root)
    if main_merged.is_err:
        return Err(main_merged.danger_err)
    worktree_merged = _load_merged(worktree)
    if worktree_merged.is_err:
        return Err(worktree_merged.danger_err)
    if draft_id not in worktree_merged.danger_ok:
        _log.error(
            "tickets: finalize_draft_for_land: %s not found in %s",
            draft_id,
            worktree,
        )
        return Err(TicketError.NotFound)
    existing = dict(main_merged.danger_ok)
    existing.update(
        {tid: t for tid, t in worktree_merged.danger_ok.items() if tid != draft_id}
    )
    final_id = _next_ticket_id_shared(main_root, existing)

    from frob.tickets import renumber_one as _renumber_one

    result = _renumber_one(worktree, draft_id, final_id)
    if result.is_err:
        return Err(result.danger_err)
    relocated = _relocate_attachment_records(worktree, draft_id, final_id)
    if relocated.is_err:
        return Err(relocated.danger_err)
    _log.info(
        "tickets: finalized draft %s -> %s (land, id ceiling fresh from main %s)",
        draft_id,
        final_id,
        main_root,
    )
    return Ok(final_id)

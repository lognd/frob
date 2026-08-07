"""T-0889 regression: a wholesale ledger write must never clobber an
externally-replaced tickets.md with a stale in-memory snapshot.

Reproduces the T-0680 field incident directly against the store layer:
`load_all`/`load_archive` some ticket map, replace tickets.md on disk out
from under that load (the section 10b `git checkout main -- tickets.md`
restore, or any other external rewrite), then call `write_all`/
`write_archive` with the now-stale map. Before the fix, the wholesale write
went through unconditionally -- silently reverting whatever the external
replacement changed (the real incident: three unrelated DONE tickets,
evidence and Done reports included, reverted to QUEUED this way).

The fix is `ledger_digest`-gated optimistic concurrency: a caller captures
`ledger_digest(ledger_path(root))` at load time and passes it back to
`write_all`/`write_archive` as `expected_digest`; a mismatch at write time
refuses loudly (`Err(TicketError.LedgerChangedSinceLoad)`) instead of
overwriting. Passing `expected_digest=None` (the default) preserves the
pre-T-0889 unconditional-overwrite behavior for not-yet-updated callers.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.tickets import Origin, Priority, Ticket, TicketError, TicketKind, TicketState
from frob.tickets._store import (
    archive_digest_map,
    archive_path,
    ledger_digest,
    ledger_digest_map,
    ledger_path,
    load_all,
    load_archive,
    write_all,
    write_archive,
    write_archived_ticket,
    write_ticket,
)


def _seed_ticket(
    root: Path,
    *,
    ticket_id: str,
    state: TicketState = TicketState.DONE,
) -> Ticket:
    """Write one ticket directly into a fresh v1 ledger (bypassing
    `new_ticket`'s id allocation) so tests can seed a known starting state;
    returns the seeded `Ticket`.

    Pins v1/'single' mode: `expected_digest` and `ledger_digest` are
    monofile primitives (one file, one content hash), and T-1553 made a
    bare `tmp_path` default to v2, where there is no single file to
    fingerprint. v2's own stale-snapshot guard is T-1588."""
    (root / "tickets.md").touch()
    (root / "tickets-archive.md").touch()
    ticket = Ticket(
        id=ticket_id,
        title=f"Seed {ticket_id}",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        priority=Priority.MEDIUM,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nseed\n",
    )
    result = write_ticket(root, ticket)
    assert result.is_ok, result.err
    return ticket


def _seed_ticket_v2(
    root: Path,
    *,
    ticket_id: str,
    state: TicketState = TicketState.DONE,
) -> Ticket:
    """`_seed_ticket`'s v2-mode twin (T-1588): writes straight through
    `write_ticket`, same as `_seed_ticket`, but relies on a bare `tmp_path`
    already defaulting to v2 (T-1553, no `tickets.md`/`tickets-archive.md`
    seed files) rather than v1's explicit monofile touch."""
    ticket = Ticket(
        id=ticket_id,
        title=f"Seed {ticket_id}",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        priority=Priority.MEDIUM,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nseed\n",
    )
    result = write_ticket(root, ticket)
    assert result.is_ok, result.err
    return ticket


class TestWriteAllRefusesAStaleSnapshot:
    """`write_all` given `expected_digest` must refuse rather than clobber
    when tickets.md changed on disk since the caller's load."""

    def test_external_replacement_between_load_and_write_all_is_refused(
        self, tmp_path: Path
    ) -> None:
        """Load the ledger, externally replace tickets.md (simulating a
        `git checkout main -- tickets.md` restore or a sibling process's
        write) with a DIFFERENT ticket's DONE state, then attempt a
        wholesale `write_all` built from the now-stale pre-replacement
        map. The write must refuse and the externally-written content must
        survive untouched."""
        _seed_ticket(tmp_path, ticket_id="T-0660", state=TicketState.DONE)

        loaded = load_all(tmp_path)
        assert loaded.is_ok, loaded.err
        stale_map = loaded.danger_ok
        digest = ledger_digest(ledger_path(tmp_path))

        # External replacement: some other actor reverts T-0660 to queued
        # and wipes its evidence -- exactly the T-0680 incident shape.
        reverted = stale_map["T-0660"].model_copy(
            update={"state": TicketState.QUEUED, "evidence": ()}
        )
        external_write = write_ticket(tmp_path, reverted)
        assert external_write.is_ok, external_write.err

        # A caller still holding the ORIGINAL (DONE) stale_map now attempts
        # a wholesale rewrite -- this must be refused, not silently applied.
        result = write_all(tmp_path, stale_map, expected_digest=digest)
        assert result.is_err
        assert result.danger_err is TicketError.LedgerChangedSinceLoad

        # The external writer's state must survive untouched.
        reloaded = load_all(tmp_path)
        assert reloaded.is_ok, reloaded.err
        assert reloaded.danger_ok["T-0660"].state is TicketState.QUEUED
        assert reloaded.danger_ok["T-0660"].evidence == ()

    def test_matching_digest_write_all_succeeds(self, tmp_path: Path) -> None:
        """When nothing changed the ledger since the load, `write_all` with
        the matching digest must still succeed normally (no false-positive
        refusal)."""
        _seed_ticket(tmp_path, ticket_id="T-0661", state=TicketState.DONE)
        loaded = load_all(tmp_path)
        assert loaded.is_ok, loaded.err
        digest = ledger_digest(ledger_path(tmp_path))

        result = write_all(tmp_path, loaded.danger_ok, expected_digest=digest)
        assert result.is_ok, result.err

    def test_no_expected_digest_preserves_unconditional_overwrite(
        self, tmp_path: Path
    ) -> None:
        """`expected_digest=None` (the default, for not-yet-updated callers)
        must preserve the pre-T-0889 unconditional-overwrite behavior --
        this guard is opt-in per caller, not a breaking default."""
        _seed_ticket(tmp_path, ticket_id="T-0719", state=TicketState.DONE)
        loaded = load_all(tmp_path)
        assert loaded.is_ok, loaded.err
        stale_map = loaded.danger_ok

        reverted = stale_map["T-0719"].model_copy(update={"state": TicketState.QUEUED})
        write_ticket(tmp_path, reverted)

        result = write_all(tmp_path, stale_map)
        assert result.is_ok, result.err
        reloaded = load_all(tmp_path)
        assert reloaded.is_ok, reloaded.err
        # unconditional overwrite: the stale DONE state wins, as before T-0889
        assert reloaded.danger_ok["T-0719"].state is TicketState.DONE


class TestWriteArchiveRefusesAStaleSnapshot:
    """Same optimistic-concurrency guard, mirrored for `write_archive`."""

    def test_external_replacement_between_load_and_write_archive_is_refused(
        self, tmp_path: Path
    ) -> None:
        """Load the (empty) archive, externally write an archived ticket,
        then attempt a stale wholesale `write_archive` -- must refuse and
        leave the external write intact."""
        # v1/'single' pin: `expected_digest` fingerprints ONE archive file,
        # which v2 does not have (T-1553 default flip; v2's guard is
        # T-1588).
        (tmp_path / "tickets.md").touch()
        (tmp_path / "tickets-archive.md").touch()
        loaded = load_archive(tmp_path)
        assert loaded.is_ok, loaded.err
        stale_map = loaded.danger_ok
        digest = ledger_digest(archive_path(tmp_path))

        external = Ticket(
            id="T-0719",
            title="External archive write",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            priority=Priority.MEDIUM,
            created=date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=(),
            evidence=(),
            attachments=(),
            body="## Description\nexternal\n",
        )
        external_write = write_archive(tmp_path, {"T-0719": external})
        assert external_write.is_ok, external_write.err

        result = write_archive(tmp_path, stale_map, expected_digest=digest)
        assert result.is_err
        assert result.danger_err is TicketError.LedgerChangedSinceLoad

        reloaded = load_archive(tmp_path)
        assert reloaded.is_ok, reloaded.err
        assert "T-0719" in reloaded.danger_ok


class TestLedgerDigest:
    """`ledger_digest` itself: the fingerprint primitive the guard above
    depends on."""

    def test_missing_ledger_digests_to_empty_string(self, tmp_path: Path) -> None:
        """A ledger path that does not exist yet digests to `""`, not an
        exception -- deliberately distinct from `None` (which `write_all`/
        `write_archive` reserve for "no check requested at all"; see
        `ledger_digest`'s docstring)."""
        assert ledger_digest(ledger_path(tmp_path)) == ""

    def test_digest_changes_when_content_changes(self, tmp_path: Path) -> None:
        """Two different ledger contents must never digest to the same
        value (the guard is only as good as this discriminating)."""
        _seed_ticket(tmp_path, ticket_id="T-0001", state=TicketState.QUEUED)
        before = ledger_digest(ledger_path(tmp_path))
        _seed_ticket(tmp_path, ticket_id="T-0002", state=TicketState.QUEUED)
        after = ledger_digest(ledger_path(tmp_path))
        assert before != after

    def test_digest_stable_for_unchanged_content(self, tmp_path: Path) -> None:
        """The same on-disk bytes must always digest identically (no
        nondeterminism -- mtime-only, hidden-timestamp, etc. would break
        this)."""
        _seed_ticket(tmp_path, ticket_id="T-0001", state=TicketState.QUEUED)
        first = ledger_digest(ledger_path(tmp_path))
        second = ledger_digest(ledger_path(tmp_path))
        assert first == second


# ---------------------------------------------------------------------------
# T-1588: v2-mode mirrors of the classes above. v2 has no single ledger
# file, so `expected_digest` there is a PER-TICKET `ledger_digest_map`/
# `archive_digest_map` snapshot, not a `ledger_digest` string -- see
# `ledger_digest_map`'s docstring for why a tree-wide digest is wrong for
# v2 (it would make every concurrent write to an UNRELATED ticket collide).
# ---------------------------------------------------------------------------


class TestWriteAllRefusesAStaleSnapshotV2:
    """`write_all`'s v2-mode guard: refuse rather than clobber when a
    ticket this call's own digest map covers changed on disk since the
    caller's load."""

    def test_external_replacement_between_load_and_write_all_is_refused(
        self, tmp_path: Path
    ) -> None:
        """Same T-0680 shape as the v1 case, mirrored against per-ticket
        `ticket.md` files: load, an external writer reverts T-0660 to
        queued, then a stale wholesale `write_all` built from the
        pre-replacement map must refuse and leave the external write
        intact."""
        _seed_ticket_v2(tmp_path, ticket_id="T-0660", state=TicketState.DONE)

        loaded = load_all(tmp_path)
        assert loaded.is_ok, loaded.err
        stale_map = loaded.danger_ok
        digest_map = ledger_digest_map(tmp_path)

        reverted = stale_map["T-0660"].model_copy(
            update={"state": TicketState.QUEUED, "evidence": ()}
        )
        external_write = write_ticket(tmp_path, reverted)
        assert external_write.is_ok, external_write.err

        result = write_all(tmp_path, stale_map, expected_digest=digest_map)
        assert result.is_err
        assert result.danger_err is TicketError.LedgerChangedSinceLoad

        reloaded = load_all(tmp_path)
        assert reloaded.is_ok, reloaded.err
        assert reloaded.danger_ok["T-0660"].state is TicketState.QUEUED
        assert reloaded.danger_ok["T-0660"].evidence == ()

    def test_matching_digest_map_write_all_succeeds(self, tmp_path: Path) -> None:
        """No false positive: an unchanged tree's digest map still matches
        at write time, so the wholesale write succeeds normally."""
        _seed_ticket_v2(tmp_path, ticket_id="T-0661", state=TicketState.DONE)
        loaded = load_all(tmp_path)
        assert loaded.is_ok, loaded.err
        digest_map = ledger_digest_map(tmp_path)

        result = write_all(tmp_path, loaded.danger_ok, expected_digest=digest_map)
        assert result.is_ok, result.err

    def test_unrelated_ticket_write_does_not_collide(self, tmp_path: Path) -> None:
        """The whole point of a per-id map over a tree-wide digest: a
        sibling write to a ticket whose id is NOT a key in this call's own
        digest map must never trip the guard -- a tree-wide digest would
        have collided here (the tree's overall content changed), a per-id
        map must not.

        (`write_all` is itself a wholesale-replace of the map it is given
        -- a ticket absent from BOTH `tickets` and `expected_digest`, like
        T-0663 below, is correctly pruned by that replace semantics, same
        as v1's `write_all`; this test is only about whether the STALENESS
        CHECK itself spuriously refuses, not about prune behavior.)"""
        _seed_ticket_v2(tmp_path, ticket_id="T-0662", state=TicketState.DONE)
        loaded = load_all(tmp_path)
        assert loaded.is_ok, loaded.err
        digest_map = ledger_digest_map(tmp_path)

        # A sibling process creates an entirely unrelated ticket after this
        # caller's load/digest snapshot -- T-0663's id is not a key in
        # `digest_map`, so it must not affect the staleness verdict below.
        _seed_ticket_v2(tmp_path, ticket_id="T-0663", state=TicketState.QUEUED)

        result = write_all(tmp_path, loaded.danger_ok, expected_digest=digest_map)
        assert result.is_ok, result.err

    def test_no_expected_digest_preserves_unconditional_overwrite(
        self, tmp_path: Path
    ) -> None:
        """`expected_digest=None` (the default) must still preserve the
        unconditional-overwrite behavior in v2 mode too -- opt-in, not a
        breaking default."""
        _seed_ticket_v2(tmp_path, ticket_id="T-0719", state=TicketState.DONE)
        loaded = load_all(tmp_path)
        assert loaded.is_ok, loaded.err
        stale_map = loaded.danger_ok

        reverted = stale_map["T-0719"].model_copy(update={"state": TicketState.QUEUED})
        write_ticket(tmp_path, reverted)

        result = write_all(tmp_path, stale_map)
        assert result.is_ok, result.err
        reloaded = load_all(tmp_path)
        assert reloaded.is_ok, reloaded.err
        assert reloaded.danger_ok["T-0719"].state is TicketState.DONE

    def test_v1_style_string_digest_in_v2_mode_is_treated_as_no_check(
        self, tmp_path: Path
    ) -> None:
        """A not-yet-updated caller that still passes the old `str`
        (`ledger_digest`) form in a v2 repo must not have it misapplied as
        a per-id digest -- `write_all` treats it the same as `None` (no
        check requested), never crashes and never refuses spuriously."""
        _seed_ticket_v2(tmp_path, ticket_id="T-0720", state=TicketState.DONE)
        loaded = load_all(tmp_path)
        assert loaded.is_ok, loaded.err

        result = write_all(tmp_path, loaded.danger_ok, expected_digest="deadbeef")
        assert result.is_ok, result.err


class TestRenumberV2StaleSnapshotGuard:
    """T-1630: `renumber(root)` (the plain contiguous-renumber path in
    `frob.tickets._new_renumber`, distinct from `renumber_one`) previously
    always captured a v1 monofile `ledger_digest(ledger_path(root))`
    snapshot before its `write_all` call, even in v2 mode -- where
    `ledger_path(root)` does not exist and `write_all` (T-1588) treats a
    bare `str` digest in v2 mode as "no check requested". That left
    `renumber(root)` with NO stale-snapshot protection in v2 mode: a
    sibling process's write between this function's `load_all` and its
    `write_all` was silently clobbered by the wholesale rewrite, the same
    T-0680 shape T-1588 already closed for `write_all`'s own primitive.
    `renumber` now snapshots via `ledger_digest_map(root)` in v2 mode
    instead, mirroring how `renumber_one` already dispatches on
    `_store_mode`."""

    def test_renumber_root_refuses_when_a_ticket_changes_under_it(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Reproduces the race directly: `renumber(root)` captures its
        stale-snapshot digest BEFORE calling `load_all`, so simulate a
        sibling writer's change landing in exactly that gap by
        monkeypatching `load_all` (as `_new_renumber` imports it) to
        perform the concurrent write itself, then return the ORIGINAL
        (now-stale, pre-race) map -- as `renumber`'s own `load_all` call
        would if it had already been in flight when the race landed.
        `renumber`'s digest snapshot was taken before this race, so it
        still reflects the PRE-race disk state; its `write_all` call at
        the end must detect the mismatch against the POST-race disk state
        and refuse.

        Before the T-1630 fix, `renumber(root)` always captured a v1
        monofile `ledger_digest(ledger_path(root))` snapshot -- meaningless
        in v2 mode, where `write_all` (T-1588) treats a bare `str` digest
        as "no check requested" -- so this exact race silently succeeded
        and reverted the concurrent write. After the fix, `renumber` must
        refuse with `Err(TicketError.LedgerChangedSinceLoad)` and leave
        the concurrent write intact."""
        from frob.tickets._new_renumber import renumber

        _seed_ticket_v2(tmp_path, ticket_id="T-0001", state=TicketState.DONE)
        _seed_ticket_v2(tmp_path, ticket_id="T-0003", state=TicketState.QUEUED)

        pristine = load_all(tmp_path)
        assert pristine.is_ok, pristine.err
        stale_snapshot = pristine.danger_ok

        def _load_all_then_race(root: Path):
            reverted = stale_snapshot["T-0001"].model_copy(
                update={"state": TicketState.QUEUED, "evidence": ()}
            )
            racing_write = write_ticket(root, reverted)
            assert racing_write.is_ok, racing_write.err
            return pristine

        import frob.tickets._new_renumber as new_renumber_module

        monkeypatch.setattr(new_renumber_module, "load_all", _load_all_then_race)

        result = renumber(tmp_path)
        assert result.is_err, (
            "renumber(root) in v2 mode must refuse when a ticket it "
            "snapshotted changed on disk before its own write_all -- it "
            f"instead returned Ok({result.ok if result.is_ok else None})"
        )
        assert result.danger_err is TicketError.LedgerChangedSinceLoad

        reloaded = load_all(tmp_path)
        assert reloaded.is_ok, reloaded.err
        assert reloaded.danger_ok["T-0001"].state is TicketState.QUEUED
        assert reloaded.danger_ok["T-0001"].evidence == ()


class TestWriteArchiveRefusesAStaleSnapshotV2:
    """Same v2 per-id guard, mirrored for `write_archive`."""

    def test_external_replacement_between_load_and_write_archive_is_refused(
        self, tmp_path: Path
    ) -> None:
        """Load the (empty) archive, externally archive-write a ticket,
        then attempt a stale wholesale `write_archive` covering that same
        id -- must refuse and leave the external write intact."""
        loaded = load_archive(tmp_path)
        assert loaded.is_ok, loaded.err
        stale_map = loaded.danger_ok

        seeded = Ticket(
            id="T-0721",
            title="Pre-existing archived ticket",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            priority=Priority.MEDIUM,
            created=date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=(),
            evidence=(),
            attachments=(),
            body="## Description\nseed\n",
        )
        assert write_archived_ticket(tmp_path, seeded).is_ok

        loaded_again = load_archive(tmp_path)
        assert loaded_again.is_ok, loaded_again.err
        stale_map = loaded_again.danger_ok
        digest_map = archive_digest_map(tmp_path)

        external = seeded.model_copy(update={"title": "Externally retitled"})
        external_write = write_archived_ticket(tmp_path, external)
        assert external_write.is_ok, external_write.err

        result = write_archive(tmp_path, stale_map, expected_digest=digest_map)
        assert result.is_err
        assert result.danger_err is TicketError.LedgerChangedSinceLoad

        reloaded = load_archive(tmp_path)
        assert reloaded.is_ok, reloaded.err
        assert reloaded.danger_ok["T-0721"].title == "Externally retitled"

    def test_matching_digest_map_write_archive_succeeds(self, tmp_path: Path) -> None:
        """No false positive when nothing changed since the load."""
        seeded = Ticket(
            id="T-0722",
            title="Archived",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            priority=Priority.MEDIUM,
            created=date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=(),
            evidence=(),
            attachments=(),
            body="## Description\nseed\n",
        )
        assert write_archived_ticket(tmp_path, seeded).is_ok

        loaded = load_archive(tmp_path)
        assert loaded.is_ok, loaded.err
        digest_map = archive_digest_map(tmp_path)

        result = write_archive(tmp_path, loaded.danger_ok, expected_digest=digest_map)
        assert result.is_ok, result.err


class TestLedgerDigestMapV2:
    """`ledger_digest_map`/`archive_digest_map` themselves: the v2
    fingerprint primitives the guards above depend on."""

    def test_non_v2_repo_returns_empty_map(self, tmp_path: Path) -> None:
        """A v1/single-mode repo has no per-ticket files to map -- must
        return `{}`, not raise."""
        (tmp_path / "tickets.md").touch()
        assert ledger_digest_map(tmp_path) == {}
        assert archive_digest_map(tmp_path) == {}

    def test_map_keys_are_ticket_ids_values_match_ledger_digest(
        self, tmp_path: Path
    ) -> None:
        """Every key is the ticket id, and every value matches
        `ledger_digest` of that ticket's own `ticket.md` file directly."""
        _seed_ticket_v2(tmp_path, ticket_id="T-0723", state=TicketState.QUEUED)
        digest_map = ledger_digest_map(tmp_path)
        assert set(digest_map) == {"T-0723"}
        from frob.tickets._store import v2_ticket_path

        assert digest_map["T-0723"] == ledger_digest(v2_ticket_path(tmp_path, "T-0723"))

    def test_archive_map_keys_are_ticket_ids(self, tmp_path: Path) -> None:
        """`archive_digest_map`'s analogous contract, over
        `tickets/archive/T-####/ticket.md`."""
        seeded = Ticket(
            id="T-0724",
            title="Archived",
            state=TicketState.DONE,
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            priority=Priority.MEDIUM,
            created=date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=(),
            evidence=(),
            attachments=(),
            body="## Description\nseed\n",
        )
        assert write_archived_ticket(tmp_path, seeded).is_ok
        digest_map = archive_digest_map(tmp_path)
        assert set(digest_map) == {"T-0724"}

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
    archive_path,
    ledger_digest,
    ledger_path,
    load_all,
    load_archive,
    write_all,
    write_archive,
    write_ticket,
)


def _seed_ticket(
    root: Path,
    *,
    ticket_id: str,
    state: TicketState = TicketState.DONE,
) -> Ticket:
    """Write one ticket directly into a fresh ledger (bypassing `new_ticket`'s
    id allocation) so tests can seed a known starting state; returns the
    seeded `Ticket`."""
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

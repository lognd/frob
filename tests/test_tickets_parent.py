"""Tests for T-2770's `set_parent` (`frob ticket set-parent <id>
<parent-id>`): the mutate-in-place parent-edge setter `frob ticket new
--parent` never got a correction path for, mirroring `set_tier`'s T-1069
shape but with real structural validation (existence, cycle,
tier-inversion, self-parent) `set_tier` deliberately does not need.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketError,
    TicketKind,
    TicketSpec,
    TicketState,
    TicketTier,
    new_ticket,
    set_parent,
)
from frob.tickets._store import (
    _serialize_ticket,
    load_all,
    load_archive,
    v2_archive_dir,
    v2_ticket_dir,
    write_ticket,
)


def _ticket(
    *,
    ticket_id: str,
    state: TicketState = TicketState.QUEUED,
    priority: Priority = Priority.MEDIUM,
    parent: str | None = None,
    tier: TicketTier = TicketTier.TICKET,
    created: date = date(2026, 1, 1),
) -> Ticket:
    """Minimal `Ticket` builder for this module's own fixtures -- same
    shape as `test_tickets_tiers.py`'s own `_ticket` helper."""
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=created,
        priority=priority,
        blocked_by=(),
        parent=parent,
        tier=tier,
        sprint=None,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body="",
    )


class TestSetParent:
    """`set_parent` (T-2770): the accountable, single-writer way to
    correct a ticket's `parent` edge, refusing every structurally invalid
    edge rather than silently accepting it (the whole point over a hand
    edit of `tickets/T-####/ticket.md`)."""

    def test_reparents_leaf_to_epic(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_reparents_leaf_to_epic  # noqa: E501
        # Positive control: a legitimate epic -> ticket edge succeeds.
        # Mirrors the measured T-2770 customer -- T-2384 (epic) gaining a
        # tier=ticket child filed with parent=null.
        epic = new_ticket(
            tmp_path,
            TicketSpec(
                title="an epic",
                kind=TicketKind.FEATURE,
                origin=Origin.HUMAN,
                tier=TicketTier.EPIC,
            ),
        )
        assert epic.is_ok
        epic_id = epic.danger_ok.id

        child = new_ticket(
            tmp_path,
            TicketSpec(
                title="a leaf ticket", kind=TicketKind.FEATURE, origin=Origin.HUMAN
            ),
        )
        assert child.is_ok
        child_id = child.danger_ok.id
        assert child.danger_ok.tier is TicketTier.TICKET

        result = set_parent(tmp_path, child_id, epic_id, reason="correcting filing")
        assert result.is_ok
        assert result.danger_ok.parent == epic_id

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok[child_id].parent == epic_id

    def test_self_parent_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_self_parent_refuses  # noqa: E501
        ticket = _ticket(ticket_id="T-0001")
        assert write_ticket(tmp_path, ticket).is_ok

        result = set_parent(tmp_path, "T-0001", "T-0001", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentSelfReference

    def test_nonexistent_parent_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_nonexistent_parent_refuses  # noqa: E501
        ticket = _ticket(ticket_id="T-0001")
        assert write_ticket(tmp_path, ticket).is_ok

        result = set_parent(tmp_path, "T-0001", "T-9999", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentNotFound

    def test_direct_cycle_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_direct_cycle_refuses  # noqa: E501
        # A parent B (B tier epic, A tier ticket); re-pointing B's parent
        # at A would close a direct ring.
        a = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET, parent="T-0002")
        b = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC, parent=None)
        assert write_ticket(tmp_path, a).is_ok
        assert write_ticket(tmp_path, b).is_ok

        result = set_parent(tmp_path, "T-0002", "T-0001", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentCycle

    def test_longer_ring_cycle_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_longer_ring_cycle_refuses  # noqa: E501
        # A -> B -> C (parent chain); re-pointing C's parent at A closes a
        # 3-node ring, not just a direct 2-node one.
        a = _ticket(ticket_id="T-0001", tier=TicketTier.EPIC, parent=None)
        b = _ticket(ticket_id="T-0002", tier=TicketTier.STORY, parent="T-0001")
        c = _ticket(ticket_id="T-0003", tier=TicketTier.TICKET, parent="T-0002")
        assert write_ticket(tmp_path, a).is_ok
        assert write_ticket(tmp_path, b).is_ok
        assert write_ticket(tmp_path, c).is_ok

        result = set_parent(tmp_path, "T-0001", "T-0003", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentCycle

    def test_tier_inversion_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_tier_inversion_refuses  # noqa: E501
        # A tier=ticket cannot parent a tier=epic.
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET)
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, leaf).is_ok
        assert write_ticket(tmp_path, epic).is_ok

        result = set_parent(tmp_path, "T-0002", "T-0001", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentTierInversion

    def test_epic_can_parent_epic(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_epic_can_parent_epic  # noqa: E501
        # Positive control: same-tier chaining is allowed, not just
        # strictly-descending tiers -- the exact T-2384->T-1382 shape
        # (both tier=epic) T-2770's own measured customer needs.
        grandparent_epic = _ticket(ticket_id="T-0001", tier=TicketTier.EPIC)
        child_epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, grandparent_epic).is_ok
        assert write_ticket(tmp_path, child_epic).is_ok

        result = set_parent(tmp_path, "T-0002", "T-0001", reason="nest epic under epic")
        assert result.is_ok
        assert result.danger_ok.parent == "T-0001"

    def test_story_cannot_parent_epic(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_story_cannot_parent_epic  # noqa: E501
        # A lower tier (story) cannot parent a higher one (epic), same
        # rule as ticket-cannot-parent-epic, one rank up.
        story = _ticket(ticket_id="T-0001", tier=TicketTier.STORY)
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, story).is_ok
        assert write_ticket(tmp_path, epic).is_ok

        result = set_parent(tmp_path, "T-0002", "T-0001", reason="test")
        assert result.is_err
        assert result.danger_err is TicketError.ParentTierInversion

    def test_reason_missing_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_reason_missing_refuses  # noqa: E501
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET)
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, leaf).is_ok
        assert write_ticket(tmp_path, epic).is_ok

        result = set_parent(tmp_path, "T-0001", "T-0002", reason="")
        assert result.is_err
        assert result.danger_err is TicketError.ParentTicketReasonMissing

    def test_moving_an_existing_parent_drops_the_old_edge(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_moving_an_existing_parent_drops_the_old_edge  # noqa: E501
        old_epic = _ticket(ticket_id="T-0001", tier=TicketTier.EPIC)
        new_epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0003", tier=TicketTier.TICKET, parent="T-0001")
        assert write_ticket(tmp_path, old_epic).is_ok
        assert write_ticket(tmp_path, new_epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        result = set_parent(tmp_path, "T-0003", "T-0002", reason="re-file under T-0002")
        assert result.is_ok
        assert result.danger_ok.parent == "T-0002"

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0003"].parent == "T-0002"

    def test_archived_ticket_routes_to_archive_path(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParent.test_archived_ticket_routes_to_archive_path  # noqa: E501
        # Mirrors T-2678's set_body fix: re-parenting an ARCHIVED ticket
        # must amend tickets/archive/<id>/ticket.md in place, never
        # materialize a fresh tickets/<id>/ active-tree duplicate.
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        assert write_ticket(tmp_path, epic).is_ok

        archived_leaf = _ticket(ticket_id="T-1688", tier=TicketTier.TICKET)
        (tmp_path / "tickets" / "archive" / "T-1688").mkdir(parents=True)
        (tmp_path / "tickets" / "archive" / "T-1688" / "ticket.md").write_text(
            _serialize_ticket(archived_leaf)
        )

        result = set_parent(tmp_path, "T-1688", "T-0002", reason="correcting filing")
        assert result.is_ok
        assert result.danger_ok.parent == "T-0002"

        archived_path = v2_archive_dir(tmp_path, "T-1688") / "ticket.md"
        assert archived_path.exists()
        assert "T-0002" in archived_path.read_text(encoding="utf-8")

        # Must-NOT-fire control: no fresh active-side copy was created.
        assert not v2_ticket_dir(tmp_path, "T-1688").exists()

        archived = load_archive(tmp_path)
        assert archived.is_ok
        assert archived.danger_ok["T-1688"].parent == "T-0002"


class TestSetParentClear:
    """T-2965: `set_parent(root, id, None, reason=...)` (`frob ticket
    set-parent <id> --clear`) -- the missing detach-to-root path. The
    original design (T-2770) only ever attached a ticket TO a parent;
    a ticket mis-parented under the wrong epic whose correct parent is
    genuinely null had no route except a hand edit or inventing a
    placeholder parent ticket just to have something valid to point
    `set-parent` at."""

    def test_clear_detaches_to_root(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentClear.test_clear_detaches_to_root  # noqa: E501
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET, parent="T-0002")
        assert write_ticket(tmp_path, epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        result = set_parent(tmp_path, "T-0001", None, reason="mis-parented, detach")
        assert result.is_ok
        assert result.danger_ok.parent is None

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].parent is None

    def test_clear_records_a_triage_entry(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentClear.test_clear_records_a_triage_entry  # noqa: E501
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET, parent="T-0002")
        assert write_ticket(tmp_path, epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        result = set_parent(tmp_path, "T-0001", None, reason="mis-parented, detach")
        assert result.is_ok
        assert len(result.danger_ok.triage_changes) == 1
        entry = result.danger_ok.triage_changes[0]
        assert entry.field == "parent"
        assert entry.old_value == "T-0002"
        assert entry.new_value is None

    def test_clear_on_already_root_ticket_refuses(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentClear.test_clear_on_already_root_ticket_refuses  # noqa: E501
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET, parent=None)
        assert write_ticket(tmp_path, leaf).is_ok

        result = set_parent(tmp_path, "T-0001", None, reason="already root")
        assert result.is_err
        assert result.danger_err is TicketError.ParentAlreadyRoot

    def test_clear_requires_a_reason(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentClear.test_clear_requires_a_reason  # noqa: E501
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET, parent="T-0002")
        assert write_ticket(tmp_path, epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        result = set_parent(tmp_path, "T-0001", None, reason="")
        assert result.is_err
        assert result.danger_err is TicketError.ParentTicketReasonMissing

    def test_clear_skips_structural_validation(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentClear.test_clear_skips_structural_validation  # noqa: E501
        # A tier=epic ticket clearing its own parent must succeed even
        # though there is nothing to validate against -- proves the
        # _validate_parent_edge path is genuinely skipped for None, not
        # merely happening to pass.
        grandparent = _ticket(ticket_id="T-0001", tier=TicketTier.EPIC)
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC, parent="T-0001")
        assert write_ticket(tmp_path, grandparent).is_ok
        assert write_ticket(tmp_path, epic).is_ok

        result = set_parent(tmp_path, "T-0002", None, reason="detach epic")
        assert result.is_ok
        assert result.danger_ok.parent is None

    def test_clear_on_archived_ticket_routes_to_archive_path(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentClear.test_clear_on_archived_ticket_routes_to_archive_path  # noqa: E501
        archived_leaf = _ticket(
            ticket_id="T-1688", tier=TicketTier.TICKET, parent="T-0002"
        )
        (tmp_path / "tickets" / "archive" / "T-1688").mkdir(parents=True)
        (tmp_path / "tickets" / "archive" / "T-1688" / "ticket.md").write_text(
            _serialize_ticket(archived_leaf)
        )

        result = set_parent(tmp_path, "T-1688", None, reason="detach archived")
        assert result.is_ok
        assert result.danger_ok.parent is None

        archived = load_archive(tmp_path)
        assert archived.is_ok
        assert archived.danger_ok["T-1688"].parent is None


class TestSetParentNoOp:
    """T-2785: setting `parent` to the value it already carries must be a
    clean no-op -- no `TriageChangeEntry`, no write at all (the file stays
    byte-identical on disk). The measured incident: an earlier caller had
    already performed the real re-parent, and a second call re-asserting
    the same value still appended `old_value == new_value` triage noise,
    which is what produced the dirty working tree in the reported
    incident (combined with defect 1 below)."""

    def test_reparenting_to_current_value_is_a_clean_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentNoOp.test_reparenting_to_current_value_is_a_clean_noop  # noqa: E501
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET, parent="T-0002")
        assert write_ticket(tmp_path, epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        ticket_path = v2_ticket_dir(tmp_path, "T-0001") / "ticket.md"
        before_bytes = ticket_path.read_bytes()

        result = set_parent(tmp_path, "T-0001", "T-0002", reason="reasserting")
        assert result.is_ok
        assert result.danger_ok.parent == "T-0002"
        assert result.danger_ok.triage_changes == ()

        after_bytes = ticket_path.read_bytes()
        assert after_bytes == before_bytes

    def test_reparenting_to_a_new_value_still_writes_exactly_one_entry(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentNoOp.test_reparenting_to_a_new_value_still_writes_exactly_one_entry  # noqa: E501
        old_epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        new_epic = _ticket(ticket_id="T-0003", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET, parent="T-0002")
        assert write_ticket(tmp_path, old_epic).is_ok
        assert write_ticket(tmp_path, new_epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        result = set_parent(tmp_path, "T-0001", "T-0003", reason="re-file")
        assert result.is_ok
        assert len(result.danger_ok.triage_changes) == 1
        entry = result.danger_ok.triage_changes[0]
        assert entry.field == "parent"
        assert entry.old_value == "T-0002"
        assert entry.new_value == "T-0003"


# frob:ticket T-4623
class TestSetParentLandInProgressGuard:
    """Asserts `set_parent` refuses before writing anything while
    `.frob/land.lock` is held, and still succeeds normally when no lock
    is held, mirroring `_reconcile`'s land-in-progress guard test shape
    (`TestReconcileApplyLandInProgressGuard`)."""

    def test_refuses_and_writes_nothing_while_land_lock_held(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        if sys.platform == "win32":
            pytest.skip("POSIX-only (T-3244)")
        # frob:tests tests/test_tickets_parent.py::TestSetParentLandInProgressGuard.test_refuses_and_writes_nothing_while_land_lock_held  # noqa: E501
        import fcntl
        import json
        import os as _os

        from frob.tickets import _setters as setters_mod
        from frob.tickets._leases import LAND_LOCK_REL, LeaseError

        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET)
        assert write_ticket(tmp_path, epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        ticket_path = v2_ticket_dir(tmp_path, "T-0001") / "ticket.md"
        before_bytes = ticket_path.read_bytes()

        lock_path = tmp_path / LAND_LOCK_REL
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder_fd = _os.open(str(lock_path), _os.O_CREAT | _os.O_RDWR, 0o644)
        fcntl.flock(holder_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _os.write(
            holder_fd,
            (json.dumps({"pid": _os.getpid(), "ticket_id": "T-9999"}) + "\n").encode(),
        )
        original = setters_mod.refuse_if_land_in_progress
        # T-2785 test seam: force wait_timeout_s=0 so this test never
        # actually waits out `refuse_if_land_in_progress`'s real bounded
        # wait -- the guard's own default budget is calibrated for a real
        # fleet, not a unit test.
        monkeypatch.setattr(
            setters_mod,
            "refuse_if_land_in_progress",
            lambda root, **_kw: original(root, wait_timeout_s=0),
        )
        try:
            result = set_parent(tmp_path, "T-0001", "T-0002", reason="test")
            assert result.is_err
            assert result.danger_err == LeaseError.LandInProgress

            # The write did not happen at all: file byte-identical, and
            # the loaded ticket's parent is still unset.
            after_bytes = ticket_path.read_bytes()
            assert after_bytes == before_bytes
            loaded = load_all(tmp_path)
            assert loaded.is_ok
            assert loaded.danger_ok["T-0001"].parent is None
        finally:
            fcntl.flock(holder_fd, fcntl.LOCK_UN)
            _os.close(holder_fd)

    def test_succeeds_normally_once_no_land_is_in_progress(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentLandInProgressGuard.test_succeeds_normally_once_no_land_is_in_progress  # noqa: E501
        # Must-still-pass control: with no land.lock at all, set_parent
        # works exactly as before this ticket -- the guard must never
        # over-refuse a genuinely free repository.
        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET)
        assert write_ticket(tmp_path, epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        result = set_parent(tmp_path, "T-0001", "T-0002", reason="test")
        assert result.is_ok
        assert result.danger_ok.parent == "T-0002"

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].parent == "T-0002"


class TestSetParentCliClearFlag:
    """T-2965: CLI-surface coverage for `frob ticket set-parent <id>
    --clear` -- `argparse.add_mutually_exclusive_group` cannot hold a
    positional, so `parent-id` is `nargs="?"` and the "exactly one of
    `parent-id` or `--clear`" rule is enforced downstream in
    `frob.app.ticket_runner._mutate._set_parent`, not by the parser
    itself. These tests exercise that split end to end: the parser
    accepts either shape, and the handler refuses the two ways they can
    conflict (both given, or neither)."""

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        # frob:tests tests/test_tickets_parent.py::TestSetParentCliClearFlag._parser  # noqa: E501
        from frob._cli_parsers._ticket._metadata import (
            _add_ticket_set_parent_parser,
        )

        top = argparse.ArgumentParser(prog="frob")
        sub = top.add_subparsers(dest="verb")
        _add_ticket_set_parent_parser(sub)
        return top

    def test_parser_accepts_clear_with_no_parent_id(self) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentCliClearFlag.test_parser_accepts_clear_with_no_parent_id  # noqa: E501
        args = self._parser().parse_args(
            ["set-parent", "T-0001", "--clear", "--reason", "detach"]
        )
        assert args.ticket_parent_clear is True
        assert args.ticket_parent_id_value is None

    def test_parser_accepts_parent_id_with_no_clear(self) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentCliClearFlag.test_parser_accepts_parent_id_with_no_clear  # noqa: E501
        args = self._parser().parse_args(
            ["set-parent", "T-0001", "T-0002", "--reason", "reparent"]
        )
        assert args.ticket_parent_clear is False
        assert args.ticket_parent_id_value == "T-0002"

    def test_parser_accepts_both_together_argparse_alone_does_not_refuse(
        self,
    ) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentCliClearFlag.test_parser_accepts_both_together_argparse_alone_does_not_refuse  # noqa: E501
        # Documents WHY the conflict check lives in _set_parent: argparse
        # itself has no positional-aware mutually-exclusive-group support,
        # so parsing both together succeeds at this layer -- the handler
        # is the only thing that refuses it (see the next test).
        args = self._parser().parse_args(
            ["set-parent", "T-0001", "T-0002", "--clear", "--reason", "x"]
        )
        assert args.ticket_parent_clear is True
        assert args.ticket_parent_id_value == "T-0002"

    def test_handler_refuses_both_parent_id_and_clear(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentCliClearFlag.test_handler_refuses_both_parent_id_and_clear  # noqa: E501
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._mutate import _set_parent

        cfg = AppConfig(
            ticket_id="T-0001",
            ticket_parent_id_value="T-0002",
            ticket_parent_clear=True,
            ticket_triage_reason="x",
        )
        with pytest.raises(SystemExit) as exc_info:
            _set_parent(tmp_path, cfg)
        assert exc_info.value.code == 1

    def test_handler_refuses_neither_parent_id_nor_clear(self, tmp_path: Path) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentCliClearFlag.test_handler_refuses_neither_parent_id_nor_clear  # noqa: E501
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._mutate import _set_parent

        cfg = AppConfig(
            ticket_id="T-0001",
            ticket_parent_id_value=None,
            ticket_parent_clear=False,
            ticket_triage_reason="x",
        )
        with pytest.raises(SystemExit) as exc_info:
            _set_parent(tmp_path, cfg)
        assert exc_info.value.code == 1

    def test_handler_clear_detaches_via_the_cli_config_shape(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_tickets_parent.py::TestSetParentCliClearFlag.test_handler_clear_detaches_via_the_cli_config_shape  # noqa: E501
        # End-to-end: an AppConfig shaped exactly like what
        # AppConfig.from_external would build from the parsed --clear
        # args reaches set_parent and actually detaches the ticket.
        from frob.app.config import AppConfig
        from frob.app.ticket_runner._mutate import _set_parent

        epic = _ticket(ticket_id="T-0002", tier=TicketTier.EPIC)
        leaf = _ticket(ticket_id="T-0001", tier=TicketTier.TICKET, parent="T-0002")
        assert write_ticket(tmp_path, epic).is_ok
        assert write_ticket(tmp_path, leaf).is_ok

        cfg = AppConfig(
            ticket_id="T-0001",
            ticket_parent_id_value=None,
            ticket_parent_clear=True,
            ticket_triage_reason="mis-parented, detach",
        )
        _set_parent(tmp_path, cfg)

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0001"].parent is None

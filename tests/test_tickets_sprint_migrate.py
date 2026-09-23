"""Tests for T-5133: sprint is a time box, milestone is the version --
`validate_sprint`/`sprint_shape_warning` (going-forward refusal/warning)
and `migrate_sprint_to_milestone` (one-shot backward migration)
(docs/modules/tickets-data-storage.md#sprint-is-a-time-box-t-5133)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.tickets import (
    Origin,
    TicketError,
    TicketKind,
    TicketSpec,
    load_active,
    new_ticket,
)
from frob.tickets._models import sprint_shape_warning, validate_sprint
from frob.tickets._sprint import migrate_sprint_to_milestone


def _init_repo(tmp_path: Path, *, scope: tuple[str, ...] = ("src/m.py",)) -> str:
    """Shared git-init + `new_ticket` fixture, same shape T-2394's own
    `test_tickets_no_scope.py::_init_repo` established."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    spec = TicketSpec(
        title="a ticket", kind=TicketKind.BUG, origin=Origin.HUMAN, scope=scope
    )
    created = new_ticket(tmp_path, spec)
    assert created.is_ok
    return created.danger_ok.id


class TestValidateSprint:
    """`validate_sprint`: refuse a semver-shaped sprint label."""

    def test_semver_shaped_refused(self) -> None:
        # frob:tests src/frob/tickets/_models.py::validate_sprint kind="unit"
        result = validate_sprint("0.531.0")
        assert result.is_err
        assert result.danger_err is TicketError.SprintIsSemverShaped

    def test_calendar_shaped_warns_not_refuses(self) -> None:
        # frob:tests src/frob/tickets/_models.py::validate_sprint kind="unit"
        result = validate_sprint("2026-W39")
        assert result.is_ok

    def test_goal_label_accepted(self) -> None:
        # frob:tests src/frob/tickets/_models.py::validate_sprint kind="unit"
        result = validate_sprint("kernel-decoupling")
        assert result.is_ok
        assert result.danger_ok == "kernel-decoupling"

    def test_semver_ack_bypasses_refusal(self) -> None:
        # frob:tests src/frob/tickets/_models.py::validate_sprint kind="unit"
        result = validate_sprint("0.531.0", semver_sprint_ack=True)
        assert result.is_ok


class TestSprintShapeWarning:
    """`sprint_shape_warning`: WARN text for a calendar/numbered label."""

    def test_calendar_shaped_warns(self) -> None:
        # frob:tests src/frob/tickets/_models.py::sprint_shape_warning kind="unit"
        assert sprint_shape_warning("2026-W39") is not None
        assert sprint_shape_warning("sprint-14") is not None

    def test_goal_label_silent(self) -> None:
        # frob:tests src/frob/tickets/_models.py::sprint_shape_warning kind="unit"
        assert sprint_shape_warning("kernel-decoupling") is None


class TestMigrateSprintToMilestone:
    """`migrate_sprint_to_milestone`: the one-shot backward repair."""

    # frob:tests src/frob/tickets/_sprint.py::SprintMigrationReport
    def test_migrates_unmilestoned_ticket(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_sprint.py::migrate_sprint_to_milestone \
        # kind="unit"
        from frob.tickets import set_sprint

        ticket_id = _init_repo(tmp_path)
        set_sprint(tmp_path, ticket_id, "v0.531.0", semver_sprint_ack=True)

        report = migrate_sprint_to_milestone(tmp_path)
        assert report.scanned == 1
        assert report.migrated == 1
        assert report.conflicts == 0

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        assert ticket.milestone == "0.531.0"
        assert ticket.sprint is None

    def test_conflict_keeps_existing_milestone(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_sprint.py::migrate_sprint_to_milestone \
        # kind="unit"
        from frob.tickets import set_milestone, set_sprint

        ticket_id = _init_repo(tmp_path)
        set_milestone(tmp_path, ticket_id, "1.0.0")
        set_sprint(tmp_path, ticket_id, "0.531.0", semver_sprint_ack=True)

        report = migrate_sprint_to_milestone(tmp_path)
        assert report.conflicts == 1
        assert report.migrated == 0

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        assert ticket.milestone == "1.0.0"
        assert ticket.sprint is None

    def test_normalizes_v_prefixed_milestone(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_sprint.py::migrate_sprint_to_milestone \
        # kind="unit"
        from frob.tickets import set_milestone

        ticket_id = _init_repo(tmp_path)
        set_milestone(tmp_path, ticket_id, "1.0.0")
        # hand-write a v-prefixed milestone past the setter's own
        # normalization, simulating a pre-T-4463 ledger row.
        ticket_path = tmp_path / "tickets" / ticket_id / "ticket.md"
        text = ticket_path.read_text()
        text = text.replace("milestone: 1.0.0", "milestone: v1.0.0")
        ticket_path.write_text(text)

        report = migrate_sprint_to_milestone(tmp_path)
        assert report.normalized == 1

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].milestone == "1.0.0"

    def test_idempotent_second_run_is_a_noop(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_sprint.py::migrate_sprint_to_milestone \
        # kind="unit"
        from frob.tickets import set_sprint

        ticket_id = _init_repo(tmp_path)
        set_sprint(tmp_path, ticket_id, "v0.531.0", semver_sprint_ack=True)

        first = migrate_sprint_to_milestone(tmp_path)
        assert first.migrated == 1

        second = migrate_sprint_to_milestone(tmp_path)
        assert second.migrated == 0
        assert second.conflicts == 0
        assert second.normalized == 0


class TestBoardGroupsByMilestoneSemverOrder:
    """T-5133 acceptance [4]: `frob ticket board` (`board_view`) groups
    tickets by milestone in semver order -- already true via `_doable_
    sort_key`'s T-2577 milestone-first sort key (real `Version` compare,
    not a string compare), this pins it down as an observed contract
    rather than leaving T-5133's own acceptance criterion unbound."""

    def test_board_orders_tickets_by_milestone_semver_not_lexical(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/tickets/__init__.py::board_view kind="unit"
        from frob.tickets import board_view, load_active, set_milestone

        low_id = _init_repo(tmp_path, scope=("src/a.py",))
        set_milestone(tmp_path, low_id, "1.9.0")
        spec = TicketSpec(
            title="second ticket",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            scope=("src/b.py",),
        )
        created = new_ticket(tmp_path, spec)
        assert created.is_ok
        high_id = created.danger_ok.id
        set_milestone(tmp_path, high_id, "1.10.0")

        reloaded = load_active(tmp_path)
        assert reloaded.is_ok
        columns = board_view(reloaded.danger_ok)
        queued_column = next(c for c in columns if c.state.value == "queued")
        ids_in_order = [t.id for t in queued_column.tickets]
        # 1.9.0 must sort BEFORE 1.10.0 (real semver order); a lexical
        # string compare would get this backwards ("1.10.0" < "1.9.0").
        assert ids_in_order.index(low_id) < ids_in_order.index(high_id)

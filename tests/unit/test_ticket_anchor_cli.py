"""T-1867: CLI wiring for `frob ticket anchor` plus `doable`'s anchor
disclosure (T-1856 follow-up).

`set_anchor` (T-1856) previously had no first-class CLI command -- only a
Python-callable library primitive. This exercises the CLI runner
(`_anchor`), its argparse registration, and `doable()`'s new
`show_anchors` filter (excluded by default, included and annotated with
`--show-anchors`).
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._mutate import _anchor
from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
    doable,
    new_ticket,
)
from frob.tickets._archive import load_active


def _git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp_path, check=True)
    return tmp_path


def _new_ticket(root: Path, title: str) -> str:
    spec = TicketSpec(title=title, kind=TicketKind.DOCS, origin=Origin.HUMAN)
    created = new_ticket(root, spec)
    assert created.is_ok
    return created.danger_ok.id


class TestAnchorCli:
    """`frob ticket anchor <id> --set|--clear --reason TEXT` forwards to
    `frob.tickets.set_anchor` (T-1856), the ONLY thing `_anchor` does."""

    def test_set_anchor_via_cli(self, tmp_path: Path) -> None:
        root = _git_repo(tmp_path)
        ticket_id = _new_ticket(root, "a permanent waiver target")

        cfg = AppConfig(
            ticket_command="anchor",
            ticket_id=ticket_id,
            ticket_anchor_set=True,
            ticket_anchor_reason="WIRE001 follow_up anchor, permanent by design",
        )
        _anchor(root, cfg)

        reloaded = load_active(root)
        assert reloaded.is_ok
        ticket = reloaded.danger_ok.tickets[ticket_id]
        assert ticket.anchor is True
        assert ticket.anchor_reason == "WIRE001 follow_up anchor, permanent by design"

    def test_clear_anchor_via_cli(self, tmp_path: Path) -> None:
        from frob.tickets._land import set_anchor

        root = _git_repo(tmp_path)
        ticket_id = _new_ticket(root, "a ticket that was anchored")
        assert set_anchor(
            root, ticket_id, anchor=True, reason="initially anchored"
        ).is_ok

        cfg = AppConfig(
            ticket_command="anchor",
            ticket_id=ticket_id,
            ticket_anchor_clear=True,
            ticket_anchor_reason="no longer needed as a waiver target",
        )
        _anchor(root, cfg)

        reloaded = load_active(root)
        assert reloaded.is_ok
        assert reloaded.danger_ok.tickets[ticket_id].anchor is False

    def test_requires_reason(self, tmp_path: Path) -> None:
        root = _git_repo(tmp_path)
        ticket_id = _new_ticket(root, "missing reason")

        cfg = AppConfig(
            ticket_command="anchor", ticket_id=ticket_id, ticket_anchor_set=True
        )
        with pytest.raises(SystemExit):
            _anchor(root, cfg)


def _ticket(
    *, ticket_id: str, state: TicketState = TicketState.QUEUED, anchor: bool = False
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"ticket {ticket_id}",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        priority=Priority.MEDIUM,
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        acceptance=(),
        threat=None,
        body="",
        anchor=anchor,
        anchor_reason="permanent WIRE001 waiver home" if anchor else None,
    )


# frob:ticket T-1867
# frob:tests tests/unit/test_ticket_anchor_cli.py::TestDoableAnchorDisclosure.test_anchor_excluded_from_default_doable  # noqa: E501
# frob:tests tests/unit/test_ticket_anchor_cli.py::TestDoableAnchorDisclosure.test_anchor_included_and_annotated_with_show_anchors  # noqa: E501
# frob:tests tests/unit/test_ticket_anchor_cli.py::TestDoableAnchorDisclosure.test_anchor_remains_queued_and_lease_eligible_either_way  # noqa: E501
class TestDoableAnchorDisclosure:
    """`doable(show_anchors=...)` (T-1867): an anchor ticket is excluded
    by default and included (still lease-eligible, still queued) only
    when a caller explicitly asks for it."""

    def test_anchor_excluded_from_default_doable(self) -> None:
        anchor = _ticket(ticket_id="T-0001", anchor=True)
        ordinary = _ticket(ticket_id="T-0002", anchor=False)
        queue = TicketQueue(tickets={"T-0001": anchor, "T-0002": ordinary})

        result = doable(queue)

        assert [t.id for t in result] == ["T-0002"]

    def test_anchor_included_and_annotated_with_show_anchors(self) -> None:
        anchor = _ticket(ticket_id="T-0001", anchor=True)
        ordinary = _ticket(ticket_id="T-0002", anchor=False)
        queue = TicketQueue(tickets={"T-0001": anchor, "T-0002": ordinary})

        result = doable(queue, show_anchors=True)

        assert {t.id for t in result} == {"T-0001", "T-0002"}

    def test_anchor_remains_queued_and_lease_eligible_either_way(self) -> None:
        # T-1867's own acceptance shape: excluding an anchor from doable's
        # RETURNED tuple must never touch the ticket's own state -- it
        # stays exactly as dispatchable (queued, no lease) as before, for
        # a caller that starts it by id explicitly or asks --show-anchors.
        anchor = _ticket(ticket_id="T-0001", anchor=True)
        queue = TicketQueue(tickets={"T-0001": anchor})

        default_result = doable(queue)
        shown_result = doable(queue, show_anchors=True)

        assert default_result == ()
        assert shown_result[0].id == "T-0001"
        assert shown_result[0].state == TicketState.QUEUED
        assert shown_result[0].anchor is True

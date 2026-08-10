"""Tests for T-2027 (found while working T-2006): `frob.serve.
_tools.frob_doable_tickets` -- the SHARED implementation both the socket
daemon RPC and the FastMCP stdio tool call -- must revalidate any
sweep-filed candidate ticket's identities before listing it, the exact
same way `frob.app.ticket_runner._query._doable`'s in-process CLI path
already does (T-2006). A client reaching this function through either
dispatch table (`_socketd._TOOL_DISPATCH`, live whenever an operator sets
`FROB_DAEMON=1`; or the FastMCP tool, unconditionally live per this
repo's own `.mcp.json`) must never see a stale, already-resolved
sweep-filed ticket that the CLI path would have already dropped.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.app.ticket_runner import _rapid_sweep
from frob.serve._tools import frob_doable_tickets


# frob:ticket T-2027
def _seed_sweep_ticket(tmp_path: Path) -> str:
    """One `bug`-kind, sweep-filed-shaped ticket naming `COV003 a.py` --
    the exact identity shape `_parse_sweep_ticket_identities` recovers,
    same construction T-2006's own `TestRevalidateDispatchableSweepTickets`
    fixtures use."""
    from frob.tickets import new_ticket
    from frob.tickets._models import Origin, TicketKind, TicketSpec

    spec = TicketSpec(
        title=f"{_rapid_sweep._REGRESSION_TITLE_PREFIX}T-1001: 1 new "
        "(rule, file) identit(ies) (COV003)",
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        scope=("a.py",),
        body=(f"{_rapid_sweep._REGRESSION_IDENTITY_HEADING}\n\n" "- COV003  a.py\n"),
    )
    created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
    assert created.is_ok
    return created.danger_ok.id


# frob:ticket T-2027
class TestFrobDoableTicketsRevalidation:
    """T-2027: `frob_doable_tickets` must reach the same
    doable set `_query._doable` would produce for the identical queue,
    not merely `doable(...)` unfiltered."""

    # frob:ticket T-2027
    @staticmethod
    def _ok_result(stdout: str):
        from typani import Ok

        class _Proc:
            def __init__(self, stdout: str) -> None:
                self.stdout = stdout
                self.returncode = 1

        return Ok(_Proc(stdout))

    # frob:ticket T-2027
    def test_resolved_sweep_ticket_is_dropped_before_listing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_serve_tools_daemon_bypass.py::TestFrobDoableTicketsRevalidation.test_resolved_sweep_ticket_is_dropped_before_listing  # noqa: E501
        ticket_id = _seed_sweep_ticket(tmp_path)

        # Fresh re-measurement: COV003/a.py no longer reproduces -- the
        # ticket is resolved.
        payload = {"results": [{"tool": "gate-summary", "diagnostics": []}]}
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )

        result = frob_doable_tickets(tmp_path)
        assert result.is_ok
        listed_ids = {row["id"] for row in result.danger_ok}
        # Before the fix: this function called `doable(...)` directly,
        # with no revalidation call at all -- the resolved sweep ticket
        # would still be listed here.
        assert ticket_id not in listed_ids

        from frob.tickets import TicketState, load_queue

        requeried = load_queue(tmp_path)
        assert requeried.is_ok
        assert requeried.danger_ok.tickets[ticket_id].state == TicketState.DROPPED

    # frob:ticket T-2027
    def test_still_reproducing_sweep_ticket_stays_listed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_serve_tools_daemon_bypass.py::TestFrobDoableTicketsRevalidation.test_still_reproducing_sweep_ticket_stays_listed  # noqa: E501
        ticket_id = _seed_sweep_ticket(tmp_path)

        payload = {
            "results": [
                {
                    "tool": "gate-summary",
                    "diagnostics": [
                        {"code": "COV003", "file": "a.py", "severity": "error"}
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: self._ok_result(json.dumps(payload)),
        )

        result = frob_doable_tickets(tmp_path)
        assert result.is_ok
        listed_ids = {row["id"] for row in result.danger_ok}
        assert ticket_id in listed_ids

    # frob:ticket T-2027
    def test_no_sweep_tickets_never_calls_revalidate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_serve_tools_daemon_bypass.py::TestFrobDoableTicketsRevalidation.test_no_sweep_tickets_never_calls_revalidate  # noqa: E501
        # An ordinary (non-sweep-filed) ticket: zero-cost, no check spawn
        # attempted at all -- matches revalidate_dispatchable_sweep_
        # tickets' own zero-cost guarantee (T-2006), proven here at the
        # call site this ticket adds, not just at the function itself.
        from frob.tickets import new_ticket
        from frob.tickets._models import Origin, TicketKind, TicketSpec

        spec = TicketSpec(
            title="an ordinary ticket, not sweep-filed",
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            scope=("b.py",),
            body="## Description\nsomething\n",
        )
        created = new_ticket(tmp_path, spec, no_commit=True, warn_if_dirty=False)
        assert created.is_ok

        called = []
        monkeypatch.setattr(
            "frob.process._guard.guarded_subprocess_run",
            lambda *a, **k: called.append(1),
        )

        result = frob_doable_tickets(tmp_path)
        assert result.is_ok
        assert called == []

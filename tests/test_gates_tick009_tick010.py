"""T-0714: TICK009 (over-broad-scope nudge, relocated from `frob ticket
doable`'s own per-invocation WARNING wall) and TICK010 (stale
cross-worktree lease report) -- both live on `tickets_gate` so `frob
check` reports them once instead of `doable` repeating them on every
queue query."""

# frob:ticket T-0714

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from frob.gates import Severity, tickets_gate
from frob.tickets import Origin, TicketKind, TicketQueue, TicketState
from frob.tickets._models import Ticket


def _ticket(ticket_id: str, scope: tuple[str, ...], state: TicketState) -> Ticket:
    return Ticket(
        id=ticket_id,
        title=f"{ticket_id} ticket",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=scope,
        body="## Description\nsomething\n",
    )


def _queue(*tickets: Ticket) -> TicketQueue:
    return TicketQueue(tickets={t.id: t for t in tickets})


class TestTick009ScopeBreadthNudges:
    def test_precisely_scoped_ticket_is_clean(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges.test_precisely_scoped_ticket_is_clean  # noqa: E501
        ticket = _ticket("T-1100", ("tests/test_gates.py",), TicketState.QUEUED)
        violations = tickets_gate(tmp_path, _queue(ticket))
        assert not any(v.rule == "TICK009" for v in violations)

    def test_chronically_over_broad_glob_warns(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges.test_chronically_over_broad_glob_warns  # noqa: E501
        ticket = _ticket("T-1101", ("src/frob/**",), TicketState.QUEUED)
        violations = [
            v for v in tickets_gate(tmp_path, _queue(ticket)) if v.rule == "TICK009"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARN
        assert "T-1101" in violations[0].message
        assert "chronically over-broad" in violations[0].message

    def test_terminal_state_ticket_excluded(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges.test_terminal_state_ticket_excluded  # noqa: E501
        ticket = _ticket("T-1102", ("src/frob/**",), TicketState.DONE)
        violations = [
            v for v in tickets_gate(tmp_path, _queue(ticket)) if v.rule == "TICK009"
        ]
        assert not violations

    # frob:ticket T-1484
    def test_scope_breadth_ack_exempts_ticket(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges.test_scope_breadth_ack_exempts_ticket  # noqa: E501
        ticket = _ticket("T-1105", ("src/frob/**",), TicketState.QUEUED)
        acked = ticket.model_copy(
            update={
                "scope_breadth_ack": True,
                "scope_breadth_ack_reason": "epic umbrella, broad by design",
            }
        )
        violations = [
            v for v in tickets_gate(tmp_path, _queue(acked)) if v.rule == "TICK009"
        ]
        assert not violations


class TestTick010StaleLeaseReport:
    def _write_lease(self, root: Path, ticket_id: str, worktree: str) -> Path:
        leases_dir = root / ".git" / "frob-leases"
        leases_dir.mkdir(parents=True, exist_ok=True)
        path = leases_dir / f"{ticket_id}.json"
        path.write_text(
            json.dumps(
                {
                    "ticket_id": ticket_id,
                    "scope": ["src/frob/**"],
                    "worktree": worktree,
                    "branch": "agent/x",
                    "recorded_at": "2026-01-01T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )
        return path

    def _init_repo(self, root: Path) -> None:
        import subprocess

        subprocess.run(["git", "init", "-q"], cwd=root, check=True)

    def test_missing_worktree_reports_once_with_path_and_remedy(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport.test_missing_worktree_reports_once_with_path_and_remedy  # noqa: E501
        self._init_repo(tmp_path)
        missing = tmp_path / "nonexistent-worktree"
        lease_path = self._write_lease(tmp_path, "T-1103", str(missing))
        violations = [
            v for v in tickets_gate(tmp_path, _queue()) if v.rule == "TICK010"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARN
        assert violations[0].file == str(lease_path)
        assert "T-1103" in violations[0].message
        assert str(missing) in violations[0].message
        assert "remove the lease file" in violations[0].message

    def test_live_worktree_is_silent(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport.test_live_worktree_is_silent  # noqa: E501
        self._init_repo(tmp_path)
        live = tmp_path / "live-worktree"
        live.mkdir()
        self._write_lease(tmp_path, "T-1104", str(live))
        violations = [
            v for v in tickets_gate(tmp_path, _queue()) if v.rule == "TICK010"
        ]
        assert not violations

    def test_five_stale_leases_each_reported_exactly_once(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport.test_five_stale_leases_each_reported_exactly_once  # noqa: E501
        self._init_repo(tmp_path)
        for i in range(5):
            self._write_lease(tmp_path, f"T-11{i:02d}", str(tmp_path / f"gone-{i}"))
        violations = [
            v for v in tickets_gate(tmp_path, _queue()) if v.rule == "TICK010"
        ]
        assert len(violations) == 5

    def test_no_leases_directory_is_silent(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport.test_no_leases_directory_is_silent  # noqa: E501
        self._init_repo(tmp_path)
        violations = [
            v for v in tickets_gate(tmp_path, _queue()) if v.rule == "TICK010"
        ]
        assert not violations

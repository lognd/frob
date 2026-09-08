"""T-0714: TICK009 (over-broad-scope nudge, relocated from `frob ticket
doable`'s own per-invocation WARNING wall) and TICK010 (stale
cross-worktree lease report, widened by T-4319 to also ERROR on a
holder-dead lease) -- both live on `tickets_gate` so `frob check` reports
them once instead of `doable` repeating them on every queue query."""

# frob:ticket T-0714
# frob:ticket T-4319

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from frob.gates import Severity, tickets_gate
from frob.tickets import Origin, TicketKind, TicketQueue, TicketState
from frob.tickets._models import Ticket
from frob.tickets._store import write_all


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
        ticket = _ticket("T-1100", ("tests/test_gates.py",), TicketState.PLANNED)
        violations = tickets_gate(tmp_path, _queue(ticket))
        assert not any(v.rule == "TICK009" for v in violations)

    def test_chronically_over_broad_glob_warns(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges.test_chronically_over_broad_glob_warns  # noqa: E501
        # T-1645: PLANNED (the state a ticket carries the instant `frob
        # ticket start` runs) is the earliest state TICK009 still fires
        # on -- the code is open and the ticket is a real, actionable
        # nudge target by this point.
        # T-3034: was "src/frob/**" -- over_broad_literal_globs (T-2771)
        # now derives package-prefix globs from tmp_path's own
        # pyproject.toml (there is none here), so "src/frob/**" no longer
        # resolves; "tests/**" is a repo-convention literal that stays in
        # OVER_BROAD_LITERAL_GLOBS regardless of package-name resolution,
        # so it still exercises TICK009's own warn path unchanged.
        ticket = _ticket("T-1101", ("tests/**",), TicketState.PLANNED)
        violations = [
            v for v in tickets_gate(tmp_path, _queue(ticket)) if v.rule == "TICK009"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARN
        assert "T-1101" in violations[0].message
        assert "chronically over-broad" in violations[0].message

    def test_in_progress_over_broad_glob_still_warns(self, tmp_path: Path) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges.test_in_progress_over_broad_glob_still_warns  # noqa: E501
        # T-1645: the ticket's own claim -- "IN-PROGRESS/done: finding as
        # today" -- verified directly, unchanged by the QUEUED exemption.
        # T-3034: was "src/frob/**" -- same over_broad_literal_globs
        # (T-2771) resolution gap as the test above.
        ticket = _ticket("T-1103", ("tests/**",), TicketState.IN_PROGRESS)
        violations = [
            v for v in tickets_gate(tmp_path, _queue(ticket)) if v.rule == "TICK009"
        ]
        assert len(violations) == 1

    # frob:ticket T-1645
    def test_queued_ticket_no_finding_even_with_broad_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges.test_queued_ticket_no_finding_even_with_broad_scope  # noqa: E501
        # T-1645: the actual bug -- a QUEUED ticket's scope is a
        # prediction, not evidence of a touched set; a chronically-broad
        # glob on a ticket nobody has started must produce ZERO TICK009
        # findings, not a warning waiting for a human to act on
        # information that does not exist yet.
        ticket = _ticket("T-1104", ("src/frob/**",), TicketState.QUEUED)
        violations = [
            v for v in tickets_gate(tmp_path, _queue(ticket)) if v.rule == "TICK009"
        ]
        assert not violations

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
        ticket = _ticket("T-1105", ("src/frob/**",), TicketState.PLANNED)
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


# frob:ticket T-4319
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

    # frob:ticket T-4319
    def _write_ticket(
        self, root: Path, ticket_id: str, state: TicketState = TicketState.IN_PROGRESS
    ) -> None:
        """Persists a real, on-disk, non-terminal ticket `lease_
        staleness_reason`'s ticket-gone/ticket-terminal checks can find
        -- required so a forced holder-dead condition is not instead
        misread as ticket-gone (T-4319's own verify-by-forcing
        requirement: the condition must be genuinely constructed, not a
        healthy-tree coincidence)."""
        ticket = Ticket(
            id=ticket_id,
            title=f"{ticket_id} ticket",
            state=state,
            kind=TicketKind.BUG,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            scope=("src/frob/gates/_tickets_gate.py",),
            body="## Description\nsomething\n",
        )
        result = write_all(root, {ticket_id: ticket})
        assert result.is_ok

    # frob:ticket T-4319
    def test_holder_dead_lease_reports_as_error_with_remedy(
        self, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport.test_holder_\
        # dead_lease_reports_as_error_with_remedy
        # T-4319: FORCE the holder-dead condition directly -- a present
        # worktree, a real non-terminal ticket, and a `recorded_at` well
        # past `LEASE_TTL_SECONDS` (so `is_lease_ttl_expired` reads
        # True) with nothing else cwd'd into the worktree (nothing ever
        # ran there) and no `land.lock` held for this ticket -- the exact
        # three-signal bar `lease_staleness_reason` requires before it
        # will call a holder dead. This is the dominant real shape T-4319
        # was filed over: worktree present and intact, holder gone.
        self._init_repo(tmp_path)
        self._write_ticket(tmp_path, "T-2200")
        present = tmp_path / "present-but-abandoned-worktree"
        present.mkdir()
        stale_recorded_at = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
        leases_dir = tmp_path / ".git" / "frob-leases"
        leases_dir.mkdir(parents=True, exist_ok=True)
        (leases_dir / "T-2200.json").write_text(
            json.dumps(
                {
                    "ticket_id": "T-2200",
                    "scope": ["src/frob/gates/_tickets_gate.py"],
                    "worktree": str(present),
                    "branch": "agent/t-2200",
                    "recorded_at": stale_recorded_at,
                }
            ),
            encoding="utf-8",
        )
        violations = [
            v for v in tickets_gate(tmp_path, _queue()) if v.rule == "TICK010"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "T-2200" in violations[0].message
        assert "frob worktree release-lease T-2200" in violations[0].message

    # frob:ticket T-4319
    def test_live_holder_lease_is_silent(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_tick009_tick010.py::TestTick010StaleLeaseReport.test_live_ho\
        # lder_lease_is_silent
        # T-4319's negative control: the SAME present worktree and real
        # ticket as above, but `recorded_at` is fresh (well within
        # `LEASE_TTL_SECONDS`) -- a slow-but-live agent must never be
        # misjudged as holder-dead. Verifying only this healthy case
        # (as the pre-T-4319 suite did) would have let a silently-wrong
        # "always dead" implementation pass; this test only means
        # something paired with the forced-dead assertion above.
        self._init_repo(tmp_path)
        self._write_ticket(tmp_path, "T-2201")
        present = tmp_path / "present-and-live-worktree"
        present.mkdir()
        fresh_recorded_at = datetime.now(UTC).isoformat()
        leases_dir = tmp_path / ".git" / "frob-leases"
        leases_dir.mkdir(parents=True, exist_ok=True)
        (leases_dir / "T-2201.json").write_text(
            json.dumps(
                {
                    "ticket_id": "T-2201",
                    "scope": ["src/frob/gates/_tickets_gate.py"],
                    "worktree": str(present),
                    "branch": "agent/t-2201",
                    "recorded_at": fresh_recorded_at,
                }
            ),
            encoding="utf-8",
        )
        violations = [
            v for v in tickets_gate(tmp_path, _queue()) if v.rule == "TICK010"
        ]
        assert not violations

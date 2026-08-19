"""tests/test_tick012_gate.py -- TICK012 (T-2561) coverage, split into its
own file rather than tests/test_gates.py: T-2550's declared scope covers
tests/test_gates.py while it is in-progress, and a CrossTicketLeakage
land-time check correctly refuses to ship a leaked commit onto a file
another open ticket owns. A standalone file with its own minimal fixtures
avoids the collision without waiting on T-2550's own close.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.gates import Severity, tickets_gate
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState


def _ticket(
    *,
    ticket_id: str,
    state: TicketState,
    scope: tuple[str, ...] = (),
) -> Ticket:
    """A minimal `Ticket` fixture -- mirrors `tests/test_gates.py::_ticket`'s
    own shape, kept local so this file has no import-time dependency on
    that (T-2550-owned, while in-progress) module."""
    return Ticket(
        id=ticket_id,
        title="Sample",
        state=state,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=scope,
        body="## Description\nx\n",
    )


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run `argv` in `cwd`, raising on a nonzero exit -- mirrors
    `tests/test_gates.py::_run`, kept local for the same reason `_ticket`
    is."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


class TestTick012LeaseScopeDrift:
    """TICK012 (T-2561): an IN_PROGRESS ticket whose live cross-worktree
    lease records a scope no longer covered by its current declared
    scope -- the write-time drift T-2547's `_effective_leakage_scope`
    empty-scope short-circuit only ever neutralized for one read site
    (CrossTicketLeakage), leaving every other `read_all_leases` consumer
    unprotected against a non-empty but still-stale lease."""

    def _queue(self, *tickets: Ticket) -> TicketQueue:
        """A `TicketQueue` of `tickets`, keyed by id."""
        return TicketQueue(tickets={t.id: t for t in tickets})

    def _repo_with_lease(
        self, tmp_path: Path, ticket_id: str, lease_scope: tuple[str, ...]
    ) -> Path:
        """A real git repo at `tmp_path` with `ticket_id`'s live lease
        file hand-written recording `lease_scope` -- `record_lease`
        itself is a no-op outside a real git worktree, so this mirrors
        `tests/test_gates.py::TestDebtGate.
        test_rel001_land_owned_via_ticket_lease`'s own direct
        `_LeaseRecord` write."""
        from frob.tickets._leases import _LeaseRecord, leases_dir

        _run(["git", "init", "-q", "-b", "main"], tmp_path)
        _run(["git", "config", "user.email", "test@example.com"], tmp_path)
        _run(["git", "config", "user.name", "Test"], tmp_path)
        (tmp_path / "tickets.md").write_text("# Tickets\n", encoding="utf-8")
        _run(["git", "add", "-A"], tmp_path)
        _run(["git", "commit", "-q", "-m", "init"], tmp_path)

        leases_root = leases_dir(tmp_path).danger_ok
        leases_root.mkdir(parents=True, exist_ok=True)
        record = _LeaseRecord(
            ticket_id=ticket_id,
            scope=lease_scope,
            worktree=str(tmp_path.resolve()),
            branch="main",
            recorded_at="2026-08-18T00:00:00+00:00",
        )
        (leases_root / f"{ticket_id}.json").write_text(
            record.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        return tmp_path

    # frob:tests tests/test_tick012_gate.py::TestTick012LeaseScopeDrift.test_stale_superset_path_fires  # noqa: E501
    def test_stale_superset_path_fires(self, tmp_path: Path) -> None:
        """Must-fire control: the lease still names `src/b.py`, but the
        ticket's declared scope has narrowed to only `src/a.py`."""
        root = self._repo_with_lease(tmp_path, "T-2600", ("src/a.py", "src/b.py"))
        ticket = _ticket(
            ticket_id="T-2600",
            state=TicketState.IN_PROGRESS,
            scope=("src/a.py",),
        )
        violations = tickets_gate(root, self._queue(ticket))
        tick012 = [v for v in violations if v.rule == "TICK012"]
        assert len(tick012) == 1
        assert tick012[0].severity == Severity.WARN
        assert "T-2600" in tick012[0].message
        assert "src/b.py" in tick012[0].message

    # frob:tests tests/test_tick012_gate.py::TestTick012LeaseScopeDrift.test_lease_matching_current_scope_is_silent  # noqa: E501
    def test_lease_matching_current_scope_is_silent(self, tmp_path: Path) -> None:
        """Must-not-fire control: the lease's recorded scope is an exact
        match for the ticket's current declared scope -- no drift."""
        root = self._repo_with_lease(tmp_path, "T-2601", ("src/a.py",))
        ticket = _ticket(
            ticket_id="T-2601",
            state=TicketState.IN_PROGRESS,
            scope=("src/a.py",),
        )
        violations = tickets_gate(root, self._queue(ticket))
        assert not any(v.rule == "TICK012" for v in violations)

    # frob:tests tests/test_tick012_gate.py::TestTick012LeaseScopeDrift.test_queued_ticket_with_no_lease_is_silent  # noqa: E501
    def test_queued_ticket_with_no_lease_is_silent(self, tmp_path: Path) -> None:
        """A QUEUED ticket (no live lease, nothing in-progress to drift)
        never fires TICK012, even with a broad declared scope."""
        _run(["git", "init", "-q", "-b", "main"], tmp_path)
        ticket = _ticket(ticket_id="T-2602", state=TicketState.QUEUED, scope=("src/**",))
        violations = tickets_gate(tmp_path, self._queue(ticket))
        assert not any(v.rule == "TICK012" for v in violations)

    # frob:tests tests/test_tick012_gate.py::TestTick012LeaseScopeDrift.test_dir_scope_still_covers_its_own_lease_paths  # noqa: E501
    def test_dir_scope_still_covers_its_own_lease_paths(self, tmp_path: Path) -> None:
        """A lease path still genuinely covered by the ticket's current
        directory-shaped declared scope (`scope_matches`'s glob
        expansion, not a literal string diff) must NOT be flagged as
        drift -- only a path `scope_matches` actually rejects counts."""
        root = self._repo_with_lease(tmp_path, "T-2603", ("src/frob/gates/_foo.py",))
        ticket = _ticket(
            ticket_id="T-2603",
            state=TicketState.IN_PROGRESS,
            scope=("src/frob/gates",),
        )
        violations = tickets_gate(root, self._queue(ticket))
        assert not any(v.rule == "TICK012" for v in violations)

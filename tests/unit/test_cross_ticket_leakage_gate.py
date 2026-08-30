"""CROSSTICKET001 gate tests (T-3466): `frob.tickets._land.
cross_ticket_leakage_gate` over a real git checkout -- the actual
acceptance criterion this ticket exists to satisfy is that `frob check
--ticket <id>` (which this gate plugs into) now reports the SAME finding
`frob ticket land`'s own T-1355 `_check_cross_ticket_leakage` preflight
already refuses on, instead of 0 errors, when run inside a ticket's own
worktree. Fixture shape (`_git_init`/`_commit_all`/the two-worktree leak
setup) deliberately duplicated from `tests/unit/test_land_step_ordering.
py::TestCrossTicketLeakagePostMutationRecheck._seed_leaked_worktree`,
matching that module's own DUP001 precedent for this exact fixture
family."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import cross_ticket_leakage_gate
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


# frob:waive DUP001 reason="same established real-git-fixture idiom tests/unit/ \
# test_land_step_ordering.py's own _run/_git_init/_commit_all already carry a waiver \
# for, citing the same real, independent shared-conftest cleanup outside any one \
# ticket's own scope"
def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


class TestCrossTicketLeakageGate:
    """`cross_ticket_leakage_gate(worktree, ticket_id)` against a real
    two-worktree leak, mirroring `_check_cross_ticket_leakage`'s own
    T-1355 acceptance shape."""

    def _seed_leaked_worktree(self, tmp_path: Path) -> tuple[Path, str, str]:
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")
        _commit_all(main_repo, "init")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], main_repo)
        wt2 = tmp_path / "wt2"
        _run(["git", "worktree", "add", "-b", "other-agent", str(wt2)], main_repo)

        held = new_ticket(wt2, _spec("Paused work", scope=("src/held.py",)))
        assert held.is_ok
        held_id = held.danger_ok.id
        assert transition(wt2, held_id, TicketState.PLANNED).is_ok
        assert transition(wt2, held_id, TicketState.IN_PROGRESS).is_ok

        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "held.py").write_text(
            "# T-held's own work, leaked onto series-a\n"
        )
        held_ticket = load_all(wt2).danger_ok[held_id]
        assert write_ticket(wt, held_ticket).is_ok
        _commit_all(wt, f"{held_id}: leaked onto series-a")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        (wt / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        return wt, held_id, landing_id

    def test_leaked_sibling_scope_fires(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_cross_ticket_leakage_gate.py::TestCrossTicketLeakageGate.test_leaked_sibling_scope_fires  # noqa: E501
        wt, held_id, landing_id = self._seed_leaked_worktree(tmp_path)

        violations = cross_ticket_leakage_gate(wt, landing_id)

        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "CROSSTICKET001"
        assert v.file == "src/held.py"
        assert held_id in v.message
        assert landing_id in v.message

    def test_no_ticket_id_is_quiet(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_cross_ticket_leakage_gate.py::TestCrossTicketLeakageGate.test_no_ticket_id_is_quiet  # noqa: E501
        wt, _held_id, _landing_id = self._seed_leaked_worktree(tmp_path)

        assert cross_ticket_leakage_gate(wt, None) == ()

    def test_no_leaked_tickets_is_quiet(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_cross_ticket_leakage_gate.py::TestCrossTicketLeakageGate.test_no_leaked_tickets_is_quiet  # noqa: E501
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")
        _commit_all(main_repo, "init")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], main_repo)
        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        (wt / "src").mkdir(exist_ok=True)
        (wt / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        assert cross_ticket_leakage_gate(wt, landing_id) == ()

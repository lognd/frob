"""T-1355: regression tests for `frob.tickets._land`'s cross-ticket
leakage preflight (`_check_cross_ticket_leakage`) -- the incident class
where landing one ticket out of a multi-ticket series worktree silently
carries a SIBLING ticket's own committed, still-open work onto main. Real
git fixture repos throughout (matching `tests/test_ticket_land.py`'s own
style for this module), not mocks -- the whole point is real `git merge
--squash` behavior against a real worktree branch.

The real incident this reproduces: worktree t-1276 hosted T-1276 (paused,
still `in-progress`) and T-1352 (an independent fix). Landing T-1352
carried T-1276's own committed files onto main while T-1276's ledger
state stayed `in-progress` -- main shipped code whose ticket the ledger
says is still open."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land
from frob.tickets._models import LandError
from frob.tickets._store import atomic_write, ledger_path, load_all, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="fixture-repo git-init boilerplate already duplicated \
# verbatim across tests/test_ticket_land.py, tests/test_ticket_merge_driver.py, \
# tests/test_tickets_collision.py, and others -- each land/ticket test module owns its \
# own tiny copy rather than importing across test files (the existing convention this \
# repo's test suite already follows for fixture helpers)"
def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)
    (root / ".gitignore").write_text(".frob/\n")


# frob:waive DUP001 reason="fixture-repo git-commit boilerplate already duplicated \
# verbatim across several land/ticket test modules -- see _git_init's waiver above for \
# the same rationale"
def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


# frob:waive DUP001 reason="fixture-repo ticket-closeability boilerplate (planned -> \
# in-progress + minimal evidence/Done-report) already duplicated verbatim in \
# tests/test_ticket_land.py -- see _git_init's waiver above for the same rationale"
def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept:
    planned -> in-progress, evidence + Done report attached."""
    assert transition(root, ticket_id, TicketState.PLANNED).is_ok
    assert transition(root, ticket_id, TicketState.IN_PROGRESS).is_ok
    loaded = load_all(root)
    ticket = loaded.danger_ok[ticket_id]
    ticket = ticket.model_copy(
        update={
            "evidence": ("tests/test_x.py::test_ok",),
            "body": ticket.body + "\n## Done report\n\nevidence attached\n",
        }
    )
    assert write_ticket(root, ticket).is_ok


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with an initialized ledger and one committed file."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


class TestCrossTicketLeakage:
    """`land()` refuses when the branch carries a sibling ticket's own
    committed, still-open work -- unless explicitly overridden."""

    def _seed_two_ticket_worktree(self, repo: Path) -> tuple[Path, str, str]:
        """One worktree hosting two tickets, mirroring the real T-1276/
        T-1352 series-worktree shape: `held.py` is committed under the
        FIRST ticket's own declared scope and left `in-progress`
        (deliberately paused); `fix.py` is a disjoint, independent second
        ticket's own change, ready to land."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "series-a", str(wt)], repo)

        held = new_ticket(wt, _spec("Paused work", scope=("src/held.py",)))
        assert held.is_ok
        held_id = held.danger_ok.id
        assert transition(wt, held_id, TicketState.PLANNED).is_ok
        assert transition(wt, held_id, TicketState.IN_PROGRESS).is_ok
        (wt / "src" / "held.py").write_text(
            "# T-held's own work, deliberately paused\n"
        )
        _commit_all(wt, f"{held_id}: paused work in flight")

        landing = new_ticket(wt, _spec("Independent fix", scope=("src/fix.py",)))
        assert landing.is_ok
        landing_id = landing.danger_ok.id
        _make_closeable(wt, landing_id)
        (wt / "src" / "fix.py").write_text("# independent fix\n")
        _commit_all(wt, f"{landing_id}: independent fix")

        return wt, held_id, landing_id

    def test_refuses_when_sibling_ticket_still_open(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage kind="unit"  # noqa: E501
        wt, held_id, landing_id = self._seed_two_ticket_worktree(repo)

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.CrossTicketLeakage
        # Nothing landed: main's tree is untouched.
        assert not (repo / "src" / "fix.py").exists()
        assert not (repo / "src" / "held.py").exists()

    def test_allow_cross_ticket_overrides_the_refusal(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage kind="unit"  # noqa: E501
        wt, held_id, landing_id = self._seed_two_ticket_worktree(repo)

        result = land(repo, landing_id, wt, dry_run=False, allow_cross_ticket=True)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()

    def test_disjoint_worktree_with_no_other_open_ticket_lands_cleanly(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage kind="unit"  # noqa: E501
        # Sanity check: a single-ticket worktree (the common case) is
        # entirely unaffected by the new preflight.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "solo", str(wt)], repo)
        created = new_ticket(wt, _spec("Solo work", scope=("src/solo.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "solo.py").write_text("# solo work\n")
        _commit_all(wt, "add solo work")

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "solo.py").exists()

    def test_sibling_ticket_already_done_on_main_does_not_block(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_check_cross_ticket_leakage kind="unit"  # noqa: E501
        # A ticket whose scope overlaps the changeset but is ALREADY done
        # (terminal) on main is not a leakage hazard -- its work already
        # shipped legitimately, so it must not block an unrelated land.
        wt, held_id, landing_id = self._seed_two_ticket_worktree(repo)

        # Mark the "held" ticket done directly on root's ledger (simulating
        # it having landed through its own, earlier `frob ticket land`).
        # held_id does not exist on root yet (only in the worktree) --
        # seed a minimal done copy on root instead, matching what a real
        # prior land would have produced.
        held_ticket = load_all(wt).danger_ok[held_id]
        done_ticket = held_ticket.model_copy(update={"state": TicketState.DONE})
        assert write_ticket(repo, done_ticket).is_ok
        _commit_all(repo, f"seed {held_id} as already-done on main")

        result = land(repo, landing_id, wt, dry_run=False)

        assert result.is_ok, result.err
        assert (repo / "src" / "fix.py").exists()

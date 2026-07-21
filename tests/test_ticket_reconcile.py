"""T-0476: `frob.tickets.reconcile` -- heal ticket<->worktree binding drift.

Real `git worktree add`/`git worktree remove` fixtures (matching
`tests/test_ticket_leases_cross_worktree.py`'s style) -- reconcile's whole
job is judging LIVE worktree state against the lease registry, which a
single in-memory tmp_path cannot exercise.

`reconcile` judges the LOCAL checkout's own `tickets.md` (an in-progress
ticket per that ledger, with no matching live lease, is a stale hold) --
this repo's real practice periodically syncs an in-progress state onto
main outside of a full land (see `tickets.md`'s history of "chore(tickets):
lease T-xxxx" commits), so a ticket can genuinely show `IN_PROGRESS` on the
checkout `reconcile` runs against while the lease that would justify it has
gone stale. The fixtures below model that directly: `_set_state_directly`
writes a ticket's ledger `state:` field WITHOUT going through `transition`
(and therefore without recording/touching a lease) -- exactly what a
lease-stamp sync onto main does; a real `transition` call in a worktree is
what actually records the lease the reconcile checks then judges live/dead.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    load_all,
    new_ticket,
    reconcile,
    transition,
)
from frob.tickets._journal import read_all_intents, write_intent
from frob.tickets._leases import read_all_leases
from frob.tickets._store import atomic_write, ledger_path, write_ticket


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


def _set_state_directly(root: Path, ticket_id: str, state: TicketState) -> None:
    """Write `ticket_id`'s `state:` field in `root`'s OWN ledger directly
    (bypassing `transition`, so no lease is recorded/touched) -- models a
    lease-stamp sync landing an in-progress state onto a checkout that
    never itself ran `frob ticket start`."""
    loaded = load_all(root)
    assert loaded.is_ok
    ticket = loaded.danger_ok[ticket_id]
    assert write_ticket(root, ticket.model_copy(update={"state": state})).is_ok


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


class TestReconcileStaleHold:
    def test_dry_run_reports_but_does_not_requeue(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_dry_run_reports_but_does_not_requeue
        created = new_ticket(repo, _spec("Stale", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-a", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        # Simulate a crashed/abandoned agent worktree, torn down without
        # ever requeuing or closing the ticket.
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)

        # Simulate the lease-stamp sync that lands the in-progress state
        # onto `repo`'s own ledger, independent of the (now-dead) lease.
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        result = reconcile(repo, apply=False)
        assert result.is_ok
        report = result.danger_ok
        assert report.requeued_tickets == (tid,)
        assert report.applied is False

        # Dry-run: the ledger is untouched.
        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.IN_PROGRESS

    def test_apply_requeues_stale_hold_and_releases_lease(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_apply_requeues_stale_hold_and_releases_lease
        created = new_ticket(repo, _spec("Stale2", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-b", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        result = reconcile(repo, apply=True)
        assert result.is_ok
        report = result.danger_ok
        assert report.requeued_tickets == (tid,)
        assert report.applied is True

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.QUEUED
        assert not any(lease.ticket_id == tid for lease in read_all_leases(repo))

    def test_live_in_progress_ticket_with_lease_is_untouched(self, repo: Path) -> None:
        """A ticket that IS in-progress with a real, live lease must never
        be reported as a stale hold -- reconcile only judges absence of a
        live lease, not the mere fact of being in-progress."""
        # frob:tests tests/test_ticket_reconcile.py::TestReconcileStaleHold.test_live_in_progress_ticket_with_lease_is_untouched
        created = new_ticket(repo, _spec("Alive", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-c", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        _set_state_directly(repo, tid, TicketState.IN_PROGRESS)

        result = reconcile(repo, apply=True)
        assert result.is_ok
        assert tid not in result.danger_ok.requeued_tickets

        loaded = load_all(repo)
        assert loaded.is_ok
        assert loaded.danger_ok[tid].state == TicketState.IN_PROGRESS

        assert transition(wt, tid, TicketState.QUEUED).is_ok
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)


class TestReconcileOrphanWorktree:
    def test_live_worktree_with_no_lease_is_flagged_not_removed(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_live_worktree_with_no_lease_is_flagged_not_removed
        wt = repo.parent / "orphan-wt"
        _run(["git", "worktree", "add", "-b", "feature-orphan", str(wt)], repo)

        result = reconcile(repo, apply=True)  # apply alone, no remove_orphans
        assert result.is_ok
        report = result.danger_ok
        assert str(wt.resolve()) in report.orphan_worktrees
        assert report.removed_worktrees == ()
        assert report.removed_orphans is False
        assert wt.exists()

        _run(["git", "worktree", "remove", "--force", str(wt)], repo)

    def test_apply_and_remove_orphans_actually_removes_it(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_apply_and_remove_orphans_actually_removes_it
        wt = repo.parent / "orphan-wt2"
        _run(["git", "worktree", "add", "-b", "feature-orphan2", str(wt)], repo)

        result = reconcile(repo, apply=True, remove_orphans=True)
        assert result.is_ok
        report = result.danger_ok
        assert str(wt.resolve()) in report.removed_worktrees
        assert report.removed_orphans is True
        assert not wt.exists()

    def test_worktree_holding_a_live_lease_is_not_orphan(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree.test_worktree_holding_a_live_lease_is_not_orphan
        created = new_ticket(repo, _spec("Held", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "add ticket")

        wt = repo.parent / "held-wt"
        _run(["git", "worktree", "add", "-b", "feature-held", str(wt)], repo)
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok

        result = reconcile(repo, apply=True, remove_orphans=True)
        assert result.is_ok
        assert str(wt.resolve()) not in result.danger_ok.orphan_worktrees
        assert wt.exists()

        assert transition(wt, tid, TicketState.QUEUED).is_ok
        _run(["git", "worktree", "remove", "--force", str(wt)], repo)


class TestReconcileOrphanedLandIntent:
    """T-0456: a `frob ticket land` intent-journal record still present
    under `repo` means the process that started that land never reached
    its own `clear_intent` cleanup (crash/interrupt mid-land)."""

    def test_dry_run_reports_but_does_not_clear(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent.test_dry_run_reports_but_does_not_clear
        write_intent(repo, "T-crashed", repo)

        result = reconcile(repo)
        assert result.is_ok
        report = result.danger_ok
        assert report.orphaned_land_intents == ("T-crashed",)
        assert report.cleared_land_intents == ()
        assert len(read_all_intents(repo)) == 1

    def test_apply_clears_the_orphaned_intent(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent.test_apply_clears_the_orphaned_intent
        write_intent(repo, "T-crashed", repo)

        result = reconcile(repo, apply=True)
        assert result.is_ok
        report = result.danger_ok
        assert report.orphaned_land_intents == ("T-crashed",)
        assert report.cleared_land_intents == ("T-crashed",)
        assert read_all_intents(repo) == ()

    def test_no_intents_reports_empty(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_reconcile.py::TestReconcileOrphanedLandIntent.test_no_intents_reports_empty
        result = reconcile(repo)
        assert result.is_ok
        assert result.danger_ok.orphaned_land_intents == ()

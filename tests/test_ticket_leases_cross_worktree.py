"""T-0473: the cross-worktree scope-lease side-channel
(`frob.tickets._leases`) -- a lease taken by `transition(..., IN_PROGRESS)`
in ONE real git worktree must be visible to `leased_by`/`doable` in a
SECOND, separate worktree of the same repository, without either worktree
merging/landing into the other. Uses real `git worktree add` checkouts
(matching `tests/test_ticket_land.py`'s style) -- the whole point of T-0473
is real cross-process/cross-checkout visibility via the shared git common
dir, which a single in-memory `tmp_path` can never exercise.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import (
    Origin,
    TicketKind,
    TicketQueue,
    TicketSpec,
    TicketState,
    doable,
    leased_by,
    load_all,
    mutate_scope,
    new_ticket,
    transition,
)
from frob.tickets._leases import _git_common_dir, read_all_leases
from frob.tickets._store import atomic_write, ledger_path


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


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with an initialized ledger and one committed file,
    plus a second linked worktree (`wt`) of the SAME repository -- the two
    real checkouts this module's tests exercise a lease across."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


@pytest.fixture
def second_worktree(repo: Path) -> Path:
    """A second linked `git worktree` of `repo`, on its own branch -- shares
    `repo`'s git common dir (and therefore its `frob-leases/` side channel)
    but has its OWN checkout of `tickets.md`."""
    wt = repo.parent / "wt"
    _run(["git", "worktree", "add", "-b", "feature-wt", str(wt)], repo)
    return wt


class TestGitCommonDir:
    def test_shared_across_linked_worktrees(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestGitCommonDir.test_shared_acro\
        # ss_linked_worktrees
        main_common = _git_common_dir(repo)
        wt_common = _git_common_dir(second_worktree)
        assert main_common.is_ok
        assert wt_common.is_ok
        assert main_common.danger_ok == wt_common.danger_ok


class TestCrossWorktreeLeaseVisibility:
    """A lease recorded by `transition(..., IN_PROGRESS)` in one worktree is
    visible via `read_all_leases`/`leased_by`/`doable` from another."""

    def test_lease_written_in_one_worktree_seen_in_another(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_lease_written_in_one_worktree_seen_in_another
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok

        leases = read_all_leases(second_worktree)
        assert any(lease.ticket_id == tid for lease in leases)
        held = next(lease for lease in leases if lease.ticket_id == tid)
        assert held.scope == ("src/feature.py",)
        assert held.worktree == str(repo.resolve())

    def test_doable_in_second_worktree_hides_colliding_ticket(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_doable_in_second_worktree_hides_colliding_ticket
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid_a = created.danger_ok.id
        assert transition(repo, tid_a, TicketState.PLANNED).is_ok
        assert transition(repo, tid_a, TicketState.IN_PROGRESS).is_ok

        # A ticket the SECOND worktree's own local ledger only knows about
        # (never dispatched in `repo`), whose scope collides with the lease
        # `repo` holds. Before T-0473, `second_worktree`'s own doable would
        # never see `tid_a`'s lease (its local `tickets.md` never had it as
        # IN_PROGRESS) and would incorrectly offer the colliding ticket.
        created_b = new_ticket(
            second_worktree, _spec("Feature B collides", scope=("src/feature.py",))
        )
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id

        loaded = load_all(second_worktree)
        assert loaded.is_ok
        queue = TicketQueue(tickets=loaded.danger_ok)
        ticket_b = queue.tickets[tid_b]
        holds = leased_by(queue, ticket_b, second_worktree)
        assert any(holder_id == tid_a for holder_id, _glob in holds)

        offered = doable(queue, second_worktree)
        assert all(t.id != tid_b for t in offered)

    def test_release_on_close_removes_the_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_release_on_close_removes_the_lease
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok
        assert any(lease.ticket_id == tid for lease in read_all_leases(second_worktree))

        assert transition(repo, tid, TicketState.QUEUED).is_ok
        assert not any(
            lease.ticket_id == tid for lease in read_all_leases(second_worktree)
        )

    def test_stale_lease_for_a_removed_worktree_is_skipped(
        self, repo: Path, second_worktree: Path, tmp_path: Path
    ) -> None:
        """A lease recording a worktree path that no longer exists on disk
        (the dead-agent case T-0476 will reconcile more fully) must not
        wedge `doable` for every other worktree forever -- `read_all_leases`
        treats it as stale and skips it."""
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_stale_lease_for_a_removed_worktree_is_skipped
        doomed_wt = repo.parent / "doomed"
        _run(["git", "worktree", "add", "-b", "feature-doomed", str(doomed_wt)], repo)
        created = new_ticket(doomed_wt, _spec("Doomed", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(doomed_wt, tid, TicketState.PLANNED).is_ok
        assert transition(doomed_wt, tid, TicketState.IN_PROGRESS).is_ok
        assert any(lease.ticket_id == tid for lease in read_all_leases(second_worktree))

        # Simulate the worktree being torn down without `git worktree
        # remove` (a crashed/abandoned agent checkout).
        _run(["git", "worktree", "remove", "--force", str(doomed_wt)], repo)
        assert not doomed_wt.exists()

        assert not any(
            lease.ticket_id == tid for lease in read_all_leases(second_worktree)
        )

    def test_scope_mutation_refreshes_the_lease(
        self, repo: Path, second_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_leases_cross_worktree.py::TestCrossWorktreeLeaseVisibility.\
        # test_scope_mutation_refreshes_the_lease
        (repo / "src" / "other.py").write_text("# other\n")
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(repo, tid, TicketState.PLANNED).is_ok
        assert transition(repo, tid, TicketState.IN_PROGRESS).is_ok

        mutated = mutate_scope(
            repo, tid, add=("src/other.py",), reason="widen for test"
        )
        assert mutated.is_ok

        leases = read_all_leases(second_worktree)
        held = next(lease for lease in leases if lease.ticket_id == tid)
        assert "src/other.py" in held.scope
        assert "src/feature.py" in held.scope

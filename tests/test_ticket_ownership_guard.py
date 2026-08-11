"""T-2079: ledger ownership -- refuse a write to a `tickets/T-####/` record
that is currently leased to a DIFFERENT worktree (the OWNERSHIP half of
T-1669's design, split off once T-1631's v2 migration made it a plain path
check).

Reproduces the T-1617 incident directly: worktree B holds a ticket's
cross-worktree lease (T-0473, `frob.tickets._leases`) while worktree A (or
the shared main checkout) tries to write that same ticket's record. Before
this ticket's fix, `write_ticket` has no idea the lease exists at all and
happily overwrites it -- that is exactly how T-1617 lost a `kind` field.

Real git fixture repos throughout (matching `tests/test_ticket_leases_cross_
worktree.py`'s own style) -- the whole point of the cross-worktree lease
side channel is real cross-checkout visibility via the shared git common
dir, which a single in-memory `tmp_path` can never exercise."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket
from frob.tickets._leases import record_lease
from frob.tickets._models import TicketError
from frob.tickets._store import write_ticket


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
    """The shared main checkout: an initialized v2 (no `tickets.md`) repo
    with one committed file."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


@pytest.fixture
def worktree_b(repo: Path) -> Path:
    """A second linked `git worktree` of `repo` -- shares `repo`'s git
    common dir (and therefore its `frob-leases/` side channel) but has its
    own checkout."""
    wt = repo.parent / "worktree_b"
    _run(["git", "worktree", "add", "-b", "t-9999", str(wt)], repo)
    return wt


class TestMainWriteToLeasedTicketIsRefused:
    """The repro: a ticket leased to `worktree_b` must not be writable from
    `repo` (the shared main checkout)."""

    def test_main_side_write_to_a_worktree_leased_ticket_is_refused(
        self, repo: Path, worktree_b: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_ownership_guard.py::TestMainWriteToLeasedTicketIsRefused.te\
        # st_main_side_write_to_a_worktree_leased_ticket_is_refused
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        ticket = created.danger_ok
        tid = ticket.id

        # worktree_b is the lease holder -- a real dispatched agent working
        # this ticket from its own worktree.
        recorded = record_lease(worktree_b, tid, ticket.scope)
        assert recorded.is_ok

        # main tries to write the SAME ticket id directly (e.g. a stray
        # `frob ticket kind`/`scope` invocation run from the shared root
        # while worktree_b still owns it) -- this must be refused, not
        # silently applied and later lost to a merge (the T-1617 shape).
        mutated = ticket.model_copy(update={"kind": TicketKind.BUG})
        result = write_ticket(repo, mutated)

        assert result.is_err, (
            "main was able to write a ticket currently leased to another "
            "worktree -- this is the T-1617 shape write_ticket must refuse"
        )
        assert result.danger_err is TicketError.TicketOwnershipViolation


class TestLeaseHolderCanStillWriteItsOwnTicket:
    """The narrow-refusal check: the lease HOLDER's own writes must keep
    working exactly as before -- this guard must never block ordinary
    single-worktree work (the T-1882 over-broad-refusal lesson)."""

    def test_holder_worktree_write_still_succeeds(
        self, repo: Path, worktree_b: Path
    ) -> None:
        # frob:tests \
        # tests/test_ticket_ownership_guard.py::TestLeaseHolderCanStillWriteItsOwnTicke\
        # t.test_holder_worktree_write_still_succeeds
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        ticket = created.danger_ok
        tid = ticket.id

        recorded = record_lease(worktree_b, tid, ticket.scope)
        assert recorded.is_ok

        mutated = ticket.model_copy(update={"kind": TicketKind.BUG})
        result = write_ticket(worktree_b, mutated)
        assert result.is_ok, result.err

    def test_unleased_ticket_is_writable_from_main(self, repo: Path) -> None:
        # frob:tests \
        # tests/test_ticket_ownership_guard.py::TestLeaseHolderCanStillWriteItsOwnTicke\
        # t.test_unleased_ticket_is_writable_from_main
        created = new_ticket(repo, _spec("Feature A", scope=("src/feature.py",)))
        assert created.is_ok
        ticket = created.danger_ok

        mutated = ticket.model_copy(update={"kind": TicketKind.BUG})
        result = write_ticket(repo, mutated)
        assert result.is_ok, result.err

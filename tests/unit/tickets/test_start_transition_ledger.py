"""T-5120: `transition(..., IN_PROGRESS)` must commit the root ledger
through `commit_ticket_ledger_change` in the SAME operation that records
the cross-worktree lease, and stamp `worktree`/`branch` onto the ticket
itself (`Ticket`'s `extra="allow"`, T-0838) -- not leave the transition as
a lease-only side effect that the ledger learns of only through a later
mirror commit (the measured 32/71-of-71 gap in T-5120's own body).

Real git fixture repo throughout (matching
`tests/test_ticket_leases_cross_worktree.py`'s own style) -- the whole
point is a real commit landing on the checkout's branch, which an
in-memory ledger can never exercise.
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
    new_ticket,
    transition,
)
from frob.tickets._store import atomic_write, ledger_path


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run `argv` in `cwd`, raising on a nonzero exit (test-helper only)."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    """Initialize a real git repo at `root` on `branch` with a test identity."""
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    """Stage and commit every change under `root` (test-helper only)."""
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _head_sha(root: Path) -> str:
    """The current HEAD commit sha of `root` (test-helper only)."""
    return _run(["git", "rev-parse", "HEAD"], root).stdout.strip()


def _spec(title: str) -> TicketSpec:
    """A minimal `TicketSpec` for this suite's fixture tickets."""
    return TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real git checkout with an initialized, committed ledger."""
    root = tmp_path / "repo"
    _git_init(root)
    atomic_write(ledger_path(root), "# Tickets\n\n")
    _commit_all(root, "init")
    return root


@pytest.fixture
def repo_with_sibling_worktree(repo: Path) -> Path:
    """A git-registered `.claude/worktrees/` agent worktree (T-0836's
    dispatch convention) of `repo` -- the fleet-dispatch shape T-5120's own
    commit-on-record-lease fix (`_commit_start_ledger_write_in_fleet_
    context`) specifically targets. Returns the AGENT worktree itself
    (matching real dispatch, where tickets are worked from `.claude/
    worktrees/<id>`, never from the primary checkout -- `record_lease`'s
    own T-2007 guard skips the primary entirely once any sibling agent
    worktree is registered, so exercising this fix from `repo` itself
    would hit that skip instead)."""
    sibling = repo / ".claude" / "worktrees" / "t-9999"
    sibling.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "worktree", "add", "-b", "t-9999", str(sibling)], repo)
    return sibling


class TestStartTransitionCommitsLedgerInFleetContext:
    """`transition(..., IN_PROGRESS)` commits the ledger immediately (via
    `record_lease` -> `commit_ticket_ledger_change`, T-5120) whenever
    dispatched agent worktrees are registered -- the multi-worktree
    fleet-dispatch shape where the generic post-dispatch auto-commit sweep
    only ever commits the CALLING worktree's own ledger, never `root`'s."""

    # frob:tests src/frob/tickets/_leases.py::_commit_start_ledger_write_in_fleet_context
    def test_in_progress_transition_commits_the_ledger(
        self, repo_with_sibling_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/unit/tickets/test_start_transition_ledger.py::TestStartTransitionCommitsLedgerInFleetContext.test_in_progress_transition_commits_the_ledger  # noqa: E501
        repo = repo_with_sibling_worktree
        created = new_ticket(repo, _spec("Feature A"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "file ticket")
        before_sha = _head_sha(repo)

        assert transition(repo, tid, TicketState.PLANNED).is_ok
        result = transition(repo, tid, TicketState.IN_PROGRESS)
        assert result.is_ok

        status = _run(["git", "status", "--porcelain", "--", "tickets.md"], repo)
        assert status.stdout.strip() == "", (
            "IN_PROGRESS transition must leave the ledger committed, not dirty"
        )
        after_sha = _head_sha(repo)
        assert after_sha != before_sha, (
            "IN_PROGRESS transition must produce a new commit on the ledger"
        )

    # frob:tests src/frob/tickets/_evidence.py::_start_transition_ledger_fields
    def test_in_progress_transition_stamps_worktree_and_branch(
        self, repo_with_sibling_worktree: Path
    ) -> None:
        # frob:tests \
        # tests/unit/tickets/test_start_transition_ledger.py::TestStartTransitionCommitsLedgerInFleetContext.test_in_progress_transition_stamps_worktree_and_branch  # noqa: E501
        repo = repo_with_sibling_worktree
        created = new_ticket(repo, _spec("Feature B"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "file ticket")

        assert transition(repo, tid, TicketState.PLANNED).is_ok
        result = transition(repo, tid, TicketState.IN_PROGRESS)
        assert result.is_ok
        updated = result.danger_ok

        assert getattr(updated, "worktree", None) == str(repo.resolve())
        assert getattr(updated, "branch", None) == "t-9999"

        # The durable ticket.md/tickets.md record -- not only the
        # gitignored `.git/frob-leases/<id>.json` side channel -- carries
        # the same worktree/branch fields, per T-5120's own acceptance.
        ledger_text = ledger_path(repo).read_text(encoding="utf-8")
        assert str(repo.resolve()) in ledger_text
        assert "t-9999" in ledger_text

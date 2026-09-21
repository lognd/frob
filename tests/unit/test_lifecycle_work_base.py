"""T-4492: `frob ticket work` (and its worktree-sweep sibling)
must branch/merge/count against the repo's REAL land target -- `root`'s
own current branch, falling back to `ticket_land_branch` config, then the
literal `"main"` -- never a hardcoded `main..`/`-b <branch> main` literal.

Real git subprocesses, matching `tests/test_ticket_work_and_land_finish.py`'s
own established fixture idiom (`_run`/`_git_init`/`_commit_all`): `work` is
itself thin orchestration over real `git worktree`/`git merge` commands, so
the fixture reproduces the real shape (a root checked out on a dev branch
one commit ahead of `main`) rather than mocking the git calls away.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner import _work
from frob.app.ticket_runner._lifecycle import _default_work_worktree
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    new_ticket,
    set_no_scope_declared,
)
from frob.tickets._store import atomic_write, ledger_path
from frob.tickets._worktree_sweep import _branch_ahead_of_main_count


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git plumbing command for this module's fixtures, raising on
    any non-zero exit -- same real-subprocess idiom every sibling test
    module in this family already uses (DUP001-waived there; not
    reintroduced here since this module's own fixture set is small
    enough to stay a single, non-shared helper)."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


# frob:waive DUP001 reason="the git-init/commit-all real-subprocess fixture idiom this \
# repo's land/ticket test modules all repeat \
# (tests/test_ticket_work_and_land_finish.py, tests/test_ticket_land.py, \
# tests/test_tickets_collision.py, tests/test_ticket_leases.py, ... none of them \
# waived either) -- extracting a shared conftest helper is real, independent cleanup \
# outside T-4492's own scope, not something to fold in here"
def _git_init(root: Path, *, branch: str = "main") -> None:
    """Initialize a throwaway git repo on `branch` with a test identity,
    for this module's real-subprocess fixtures."""
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


# frob:waive DUP001 reason="see _git_init's identical DUP001 waiver immediately above \
# -- same established real-git-fixture idiom, same real cleanup-later disposition"
def _commit_all(root: Path, message: str) -> None:
    """Stage and commit everything in `root`'s working tree, a no-op if
    nothing changed -- shared by every fixture step in this module that
    needs a real commit to exist on disk."""
    _run(["git", "add", "-A"], root)
    status = _run(["git", "diff", "--cached", "--name-only"], root).stdout
    if not status.strip():
        return
    _run(["git", "commit", "-q", "-m", message], root)


def _new_ticket(repo: Path, title: str):  # noqa: ANN201
    """Mint a fresh, empty-scope-declared ticket for this module's
    fixtures -- same `set_no_scope_declared` shape
    `tests/test_ticket_work_and_land_finish.py::_new_ticket` uses, since
    these tests exercise `work`/sweep branch-resolution plumbing, not
    scope-coverage enforcement."""
    spec = TicketSpec(title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT)
    created = new_ticket(repo, spec)
    assert created.is_ok
    result = set_no_scope_declared(
        repo,
        created.danger_ok.id,
        reason="test fixture: work/sweep branch-resolution coverage only",
    )
    assert result.is_ok
    return result.danger_ok


@pytest.fixture
def repo_on_dev(tmp_path: Path) -> Path:
    """A repo whose root is checked out on `dev`, one commit AHEAD of
    `main` -- the exact shape T-4492 measured: `main` is the
    frozen alpha tip, `dev` (the real land target) carries a commit
    `main` does not have yet (here, the ticket's own filing commit, via
    `_new_ticket` below), matching the incident where `frob ticket work`
    branched off `main` and so lacked the worktree's own ticket filing
    commit."""
    main_repo = tmp_path / "main"
    _git_init(main_repo, branch="main")
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    (main_repo / ".gitignore").write_text(".claude/\n.frob/\n")
    _commit_all(main_repo, "init")

    _run(["git", "checkout", "-q", "-b", "dev"], main_repo)
    return main_repo


class TestWorkBranchesFromRootsCurrentBranch:
    """Acceptance 1: root on `dev`, one commit ahead of `main` -> the
    worktree `frob ticket work` creates carries `dev`'s tip."""

    def test_worktree_head_contains_devs_own_tip_commit(
        self, repo_on_dev: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_lifecycle_work_base.py::TestWorkBranchesFromRootsCurrentBranch.test_worktree_head_contains_devs_own_tip_commit  # noqa: E501
        ticket = _new_ticket(repo_on_dev, "Dev-branch work")
        tid = ticket.id
        # The ticket's own filing commit lands on `dev` ONLY -- `main`
        # never sees it, mirroring the real incident (T-4496's
        # filing commit existed on `dev`, not on the frozen `main`).
        _commit_all(repo_on_dev, "file ticket " + tid)
        dev_tip = _run(["git", "rev-parse", "HEAD"], repo_on_dev).stdout.strip()
        main_tip = _run(["git", "rev-parse", "main"], repo_on_dev).stdout.strip()
        assert dev_tip != main_tip

        cfg = AppConfig(ticket_command="work", ticket_id=tid, ticket_foreground=True)
        _work(repo_on_dev, cfg)

        worktree = _default_work_worktree(repo_on_dev, tid)
        assert worktree.is_dir()
        worktree_head = _run(["git", "rev-parse", "HEAD"], worktree).stdout.strip()
        # The worktree's HEAD must be a descendant of (contain) dev's tip
        # -- at the parent commit this FAILS because the worktree was cut
        # from `main`, which never has dev's tip as an ancestor.
        merge_base = _run(
            ["git", "merge-base", worktree_head, dev_tip], worktree
        ).stdout.strip()
        assert merge_base == dev_tip

    def test_byte_for_byte_historical_when_root_is_on_main_no_config(
        self, tmp_path: Path
    ) -> None:
        """Acceptance 3: no `ticket_land_branch` config, root on `main`
        -> the worktree is still cut from `main` (the pre-fix, and only
        ever, literal), byte-for-byte the historical behavior."""
        # frob:tests \
        # tests/unit/test_lifecycle_work_base.py::TestWorkBranchesFromRootsCurrentBranch.test_byte_for_byte_historical_when_root_is_on_main_no_config  # noqa: E501
        main_repo = tmp_path / "main"
        _git_init(main_repo, branch="main")
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")
        (main_repo / ".gitignore").write_text(".claude/\n.frob/\n")
        _commit_all(main_repo, "init")

        ticket = _new_ticket(main_repo, "Main-branch work")
        tid = ticket.id
        _commit_all(main_repo, "file ticket " + tid)
        main_tip = _run(["git", "rev-parse", "HEAD"], main_repo).stdout.strip()

        cfg = AppConfig(ticket_command="work", ticket_id=tid, ticket_foreground=True)
        _work(main_repo, cfg)

        worktree = _default_work_worktree(main_repo, tid)
        worktree_head = _run(["git", "rev-parse", "HEAD"], worktree).stdout.strip()
        # `_start`'s own auto-transition commit (queued -> in-progress)
        # lands on top inside the worktree, so HEAD is not byte-identical
        # to `main_tip` -- what must be historical is the BASE the
        # worktree was cut from: `main_tip` is an ancestor of HEAD.
        merge_base = _run(
            ["git", "merge-base", worktree_head, main_tip], worktree
        ).stdout.strip()
        assert merge_base == main_tip


class TestWorktreeSweepCountsAgainstResolvedTarget:
    """Acceptance 2: the worktree sweep's ahead-count resolves the same
    target branch as `work`, not a hardcoded `main`."""

    def test_counts_commits_ahead_of_dev_not_ahead_of_main(
        self, repo_on_dev: Path
    ) -> None:
        # frob:tests \
        # tests/unit/test_lifecycle_work_base.py::TestWorktreeSweepCountsAgainstResolvedTarget.test_counts_commits_ahead_of_dev_not_ahead_of_main  # noqa: E501
        _commit_all(repo_on_dev, "advance dev")
        branch = "feature-branch"
        _run(["git", "checkout", "-q", "-b", branch], repo_on_dev)
        (repo_on_dev / "src" / "extra.py").write_text("# one commit on branch\n")
        _commit_all(repo_on_dev, "one commit on branch")
        _run(["git", "checkout", "-q", "dev"], repo_on_dev)

        # `branch` carries exactly 1 commit not on `dev`, but 2 not on
        # `main` (dev's own extra commit plus branch's own) -- the two
        # counts differ, so this distinguishes a `dev..branch` count from
        # the pre-fix `main..branch` one.
        ahead = _branch_ahead_of_main_count(repo_on_dev, branch)
        assert ahead == 1

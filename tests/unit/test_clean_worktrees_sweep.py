"""T-4437 (F-055 class): leaked BUG002-repro/land-squash `git worktree
add` scratch dirs never got swept by `frob doctor`/`frob clean` -- a
killed land or a killed check run skips both pipelines' own happy-path
cleanup (a `finally`/`with tempfile.TemporaryDirectory`, neither of which
runs under SIGKILL). `sweep_disposable_worktrees` finds them under a
scan root, decides liveness from a creator-stamped owner-pid file
(`stamp_owner_pid`), and removes the dead ones; `frob clean
--sweep-disposable-worktrees` is the CLI surface."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from frob.app.clean_runner import run as clean_run
from frob.app.config import AppConfig
from frob.worktrees._disposable_sweep import (
    OWNER_PID_FILENAME,
    stamp_owner_pid,
    sweep_disposable_worktrees,
)


def _git(root: Path, *args: str) -> None:
    """Run a `git` subcommand quietly against `root`, raising on failure."""
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A minimal initialized-and-committed git repo, real enough for
    `git worktree add`/`remove`/`prune` to operate on."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "f.py").write_text("x = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _make_disposable(scan_root: Path, prefix: str, *, repo: Path) -> Path:
    """A `<scan_root>/<prefix>-*/wt` scratch dir with a real `git worktree
    add`-registered checkout inside it -- test helper mirroring what
    `frob.gates._bug_repro`/`frob.tickets._land_compose` actually cut."""
    scratch = scan_root / f"{prefix}-abc123"
    scratch.mkdir()
    worktree = scratch / "wt"
    _git(repo, "worktree", "add", "--detach", "-q", str(worktree), "HEAD")
    return scratch


# frob:ticket T-4437
class TestSweepDisposableWorktrees:
    """`sweep_disposable_worktrees`'s liveness classification and removal
    (T-4437 acceptance criteria 1-3)."""

    # frob:tests src/frob/worktrees/_disposable_sweep.py::sweep_disposable_worktrees  # noqa: E501
    # frob:tests src/frob/worktrees/_disposable_sweep.py::DisposableWorktreeEntry  # noqa: E501
    def test_dead_stamped_worktree_is_removed(
        self, tmp_path: Path, git_repo: Path
    ) -> None:
        """A scratch dir stamped with a pid that is NOT running is dead
        and gets removed when `execute=True` -- `git worktree list`
        forgets it too (criterion 3)."""
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        scratch = _make_disposable(scan_root, "frob-bug002", repo=git_repo)
        # a pid vanishingly unlikely to be alive
        (scratch / OWNER_PID_FILENAME).write_text("999999")

        report = sweep_disposable_worktrees(git_repo, execute=True, scan_root=scan_root)

        assert len(report.removed) == 1
        assert report.removed[0].scratch == scratch
        assert not scratch.exists()
        listing = subprocess.run(
            ["git", "-C", str(git_repo), "worktree", "list"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        # frob:tests src/frob/worktrees/_disposable_sweep.py::sweep_disposable_worktrees  # noqa: E501
        assert "wt" not in listing

    def test_live_stamped_worktree_is_kept(
        self, tmp_path: Path, git_repo: Path
    ) -> None:
        """A scratch dir stamped with THIS test's own (definitely live)
        pid is left alone."""
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        scratch = _make_disposable(scan_root, "frob-land-squash", repo=git_repo)
        stamp_owner_pid(scratch)

        report = sweep_disposable_worktrees(git_repo, execute=True, scan_root=scan_root)

        assert report.removed == ()
        assert len(report.kept) == 1
        assert scratch.exists()

    def test_unstamped_worktree_is_removed(
        self, tmp_path: Path, git_repo: Path
    ) -> None:
        """A pre-T-4437-shaped leak (no owner-pid stamp at all) is treated
        as dead -- nothing left to be alive."""
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        scratch = _make_disposable(scan_root, "frob-bug002", repo=git_repo)

        report = sweep_disposable_worktrees(git_repo, execute=True, scan_root=scan_root)

        assert len(report.removed) == 1
        assert not scratch.exists()

    def test_dry_run_reports_without_removing(
        self, tmp_path: Path, git_repo: Path
    ) -> None:
        """`execute=False` reports the dead candidate in `removed` but
        never deletes it -- the dry-run preview contract."""
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        scratch = _make_disposable(scan_root, "frob-bug002", repo=git_repo)

        report = sweep_disposable_worktrees(
            git_repo, execute=False, scan_root=scan_root
        )

        assert len(report.removed) == 1
        assert scratch.exists()


# frob:ticket T-4437
class TestStampOwnerPid:
    """`stamp_owner_pid` (T-4437 acceptance criterion 2)."""

    def test_writes_current_pid(self, tmp_path: Path) -> None:
        """The stamp file contains this process's own pid, readable back
        as the int `os.getpid()` returned."""
        stamp_owner_pid(tmp_path)
        assert (tmp_path / OWNER_PID_FILENAME).read_text().strip() == str(os.getpid())


# frob:ticket T-4437
class TestCleanSweepDisposableWorktreesFlag:
    """`frob clean --sweep-disposable-worktrees`'s CLI dispatch (T-4437)."""

    def test_flag_dispatches_to_sweep(
        self, tmp_path: Path, git_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`clean_sweep_worktrees=True` prints the disposable-sweep report
        (not the ordinary tiered-artifact one) and does not raise."""
        scan_root = tmp_path / "scan"
        scan_root.mkdir()
        _make_disposable(scan_root, "frob-bug002", repo=git_repo)
        cfg = AppConfig(
            clean_path=git_repo,
            clean_sweep_worktrees=True,
        )
        # dispatch runs against tempfile.gettempdir() internally when no
        # scan_root override is threaded through the CLI path -- this
        # test only asserts the flag routes to the sweep report renderer
        # without raising; `sweep_disposable_worktrees`'s own scan-root
        # behavior is covered directly above.
        clean_run(cfg)
        out = capsys.readouterr().out
        assert "sweep-disposable-worktrees" in out

"""T-0738: worktree warm pool (`frob.scaffold._pool`) -- exercised against
throwaway `tmp_path` git repos only. NEVER point this module's fixtures at
the real `frob` clone or any of its existing worktrees: `warm_worktree`/
`lease_worktree` really do run `git worktree add`/`git merge`, and a test
repo of our own is the only safe target."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from typani import Err, Ok
from typani.result import Result

from frob.scaffold._pool import (
    PoolError,
    default_pool_dir,
    lease_worktree,
    pool_status,
    read_manifest,
    warm_pool,
    warm_worktree,
)


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command in `cwd`, raising on failure -- setup helper only."""
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal one-commit git repo at `tmp_path/repo` with a `main`
    branch, suitable as `repo_root` for every test in this file."""
    root = tmp_path / "repo"
    root.mkdir()
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "README.md").write_text("hello\n")
    _git("add", "README.md", cwd=root)
    _git("commit", "-q", "-m", "initial", cwd=root)
    return root


def _fake_build_ok(_path: Path) -> Result[None, PoolError]:
    """A `build_fn` stand-in that always succeeds instantly -- every test
    here injects this (or `_fake_build_fail`) instead of the real default
    (`make core`), which would try to compile native extensions inside a
    throwaway one-commit test repo."""
    return Ok(None)


def _fake_build_fail(_path: Path) -> Result[None, PoolError]:
    """A `build_fn` stand-in that always fails, for the not-ready path."""
    return Err(PoolError.BuildFailed)


# frob:ticket T-0738
class TestDefaultPoolDir:
    """`default_pool_dir` resolution."""

    # frob:ticket T-0738
    def test_resolves_under_git_common_dir(self, repo: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestDefaultPoolDir.test_resolves_under_gi\
        # t_common_dir  # noqa: E501
        """The default pool dir lives under `<repo>/.git/frob-pool` for a
        non-worktree, single-checkout repo (its own git common dir)."""
        result = default_pool_dir(repo)
        assert result.is_ok
        assert result.danger_ok == (repo / ".git" / "frob-pool")


# frob:ticket T-0738
class TestManifestRoundTrip:
    """Manifest read/write round-tripping."""

    # frob:ticket T-0738
    def test_write_then_read_round_trips(self, repo: Path, tmp_path: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestManifestRoundTrip.test_write_then_rea\
        # d_round_trips  # noqa: E501
        """A slot warmed via `warm_worktree` is readable back via
        `read_manifest` with the same index/ready/path."""
        pool_dir = tmp_path / "pool"
        result = warm_worktree(repo, pool_dir, 0, build_fn=_fake_build_ok)
        assert result.is_ok, result
        entry = result.danger_ok
        assert entry.ready is True
        assert entry.index == 0

        reread = read_manifest(pool_dir)
        assert reread.is_ok
        assert len(reread.danger_ok) == 1
        assert reread.danger_ok[0].path == entry.path


# frob:ticket T-0738
class TestWarmWorktree:
    """`warm_worktree`: git worktree add + build step + manifest entry."""

    # frob:ticket T-0738
    def test_creates_worktree_and_marks_ready(self, repo: Path, tmp_path: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestWarmWorktree.test_creates_worktree_an\
        # d_marks_ready  # noqa: E501
        """A successful build marks the slot ready and the worktree path
        actually exists with a checked-out working tree."""
        pool_dir = tmp_path / "pool"
        result = warm_worktree(repo, pool_dir, 0, build_fn=_fake_build_ok)
        assert result.is_ok, result
        entry = result.danger_ok
        assert entry.ready is True
        assert Path(entry.path).is_dir()
        assert (Path(entry.path) / "README.md").exists()

    # frob:ticket T-0738
    def test_build_failure_marks_not_ready(self, repo: Path, tmp_path: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestWarmWorktree.test_build_failure_marks\
        # _not_ready  # noqa: E501
        """A build step that fails still leaves the worktree on disk (not
        silently discarded) but records `ready=False`."""
        pool_dir = tmp_path / "pool"
        result = warm_worktree(repo, pool_dir, 0, build_fn=_fake_build_fail)
        assert result.is_ok, result
        entry = result.danger_ok
        assert entry.ready is False
        assert Path(entry.path).is_dir()


# frob:ticket T-0738
class TestWarmPool:
    """`warm_pool`: filling a pool to N slots, idempotently."""

    # frob:ticket T-0738
    def test_fills_pool_to_n_slots(self, repo: Path, tmp_path: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestWarmPool.test_fills_pool_to_n_slots  \
        # # noqa: E501
        """Warming a pool of size 3 produces exactly 3 ready entries."""
        pool_dir = tmp_path / "pool"
        result = warm_pool(repo, 3, pool_dir=pool_dir, build_fn=_fake_build_ok)
        assert result.is_ok, result
        entries = result.danger_ok
        assert len(entries) == 3
        assert all(e.ready for e in entries)
        assert sorted(e.index for e in entries) == [0, 1, 2]

    # frob:ticket T-0738
    def test_leaves_existing_ready_slots_alone(
        self, repo: Path, tmp_path: Path
    ) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestWarmPool.test_leaves_existing_ready_s\
        # lots_alone  # noqa: E501
        """Re-running `warm_pool` after slot 0 is already ready does not
        recreate it -- its `created_at` timestamp is unchanged."""
        pool_dir = tmp_path / "pool"
        first = warm_pool(repo, 1, pool_dir=pool_dir, build_fn=_fake_build_ok)
        assert first.is_ok
        first_created_at = first.danger_ok[0].created_at

        second = warm_pool(repo, 2, pool_dir=pool_dir, build_fn=_fake_build_ok)
        assert second.is_ok, second
        entries = {e.index: e for e in second.danger_ok}
        assert len(entries) == 2
        assert entries[0].created_at == first_created_at


# frob:ticket T-0738
class TestLeaseWorktree:
    """`lease_worktree`: handing out and refilling a pool slot."""

    # frob:ticket T-0738
    def test_leases_ready_slot_and_removes_it(self, repo: Path, tmp_path: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestLeaseWorktree.test_leases_ready_slot_\
        # and_removes_it  # noqa: E501
        """Leasing removes the slot from the manifest immediately (before
        any background refill completes)."""
        pool_dir = tmp_path / "pool"
        warmed = warm_pool(repo, 1, pool_dir=pool_dir, build_fn=_fake_build_ok)
        assert warmed.is_ok

        leased = lease_worktree(repo, pool_dir=pool_dir, refill=False)
        assert leased.is_ok, leased
        assert leased.danger_ok.index == 0

        status = pool_status(repo, pool_dir=pool_dir)
        assert status.is_ok
        assert status.danger_ok == ()

    # frob:ticket T-0738
    def test_empty_pool_returns_err(self, repo: Path, tmp_path: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestLeaseWorktree.test_empty_pool_returns\
        # _err  # noqa: E501
        """Leasing from a pool with no ready slots (never warmed) is
        `Err(Empty)`, not a crash."""
        pool_dir = tmp_path / "pool"
        result = lease_worktree(repo, pool_dir=pool_dir, refill=False)
        assert result.is_err
        assert result.danger_err is PoolError.Empty

    # frob:ticket T-0738
    def test_lease_merges_base_ref_current(self, repo: Path, tmp_path: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestLeaseWorktree.test_lease_merges_base_\
        # ref_current  # noqa: E501
        """A commit landed on `main` AFTER a slot was warmed is present in
        the leased worktree once `lease_worktree` merges it in."""
        pool_dir = tmp_path / "pool"
        warmed = warm_pool(repo, 1, pool_dir=pool_dir, build_fn=_fake_build_ok)
        assert warmed.is_ok

        (repo / "NEWFILE.txt").write_text("new\n")
        _git("add", "NEWFILE.txt", cwd=repo)
        _git("commit", "-q", "-m", "second commit", cwd=repo)

        leased = lease_worktree(repo, pool_dir=pool_dir, refill=False)
        assert leased.is_ok, leased
        assert (Path(leased.danger_ok.path) / "NEWFILE.txt").exists()


# frob:ticket T-0738
class TestRefillAsync:
    """`refill_pool_async`: background re-warm after a lease."""

    # frob:ticket T-0738
    def test_refill_thread_rewarms_slot(self, repo: Path, tmp_path: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestRefillAsync.test_refill_thread_rewarm\
        # s_slot  # noqa: E501
        """Leasing with `refill=True` (the default) eventually re-warms
        the same slot index in the background; join the internal thread
        deterministically via `refill_pool_async` directly instead of
        sleeping/polling for the lease call's own thread."""
        from frob.scaffold._pool import refill_pool_async

        pool_dir = tmp_path / "pool"
        warmed = warm_pool(repo, 1, pool_dir=pool_dir, build_fn=_fake_build_ok)
        assert warmed.is_ok

        leased = lease_worktree(repo, pool_dir=pool_dir, refill=False)
        assert leased.is_ok

        thread = refill_pool_async(repo, 0, pool_dir=pool_dir, build_fn=_fake_build_ok)
        thread.join(timeout=30.0)
        assert not thread.is_alive()

        status = pool_status(repo, pool_dir=pool_dir)
        assert status.is_ok
        assert len(status.danger_ok) == 1
        assert status.danger_ok[0].ready is True


# frob:ticket T-0738
class TestPoolStatus:
    """`pool_status`: read-only manifest inspection."""

    # frob:ticket T-0738
    def test_status_reflects_manifest(self, repo: Path, tmp_path: Path) -> None:
        # frob:tests \
        # tests/system/test_scaffold_pool.py::TestPoolStatus.test_status_reflects_manif\
        # est  # noqa: E501
        """`pool_status` returns exactly what was just warmed."""
        pool_dir = tmp_path / "pool"
        warmed = warm_pool(repo, 2, pool_dir=pool_dir, build_fn=_fake_build_ok)
        assert warmed.is_ok

        status = pool_status(repo, pool_dir=pool_dir)
        assert status.is_ok
        assert len(status.danger_ok) == 2

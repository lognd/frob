"""T-0507: the worktree-lease guard extended to `frob release stamp`
(the T-0431 pattern applied to `frob.release.stamp`)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.graph import GraphSnapshot
from frob.release import ReleaseError, stamp
from frob.tickets._worktree_guard import FROB_WORKTREE_ENV


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "x.txt").write_text("x\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


class TestStampWorktreeLease:
    def test_mismatched_lease_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_release_worktree_lease.py::TestStampWorktreeLease.test_mismatched_lease_refuses  # noqa: E501
        _init_repo(tmp_path)
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(tmp_path / "elsewhere"))
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        result = stamp(tmp_path, snapshot, "0.1.0")
        assert result.is_err
        assert result.danger_err == ReleaseError.WorktreeLeaseViolation
        assert not (tmp_path / ".frob-release.json").exists()

    def test_no_lease_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_release_worktree_lease.py::TestStampWorktreeLease.test_no_lease_succeeds  # noqa: E501
        monkeypatch.delenv(FROB_WORKTREE_ENV, raising=False)
        _init_repo(tmp_path)
        snapshot = GraphSnapshot(root=str(tmp_path), symbols={}, edges=())
        result = stamp(tmp_path, snapshot, "0.1.0")
        assert result.is_ok
        assert (tmp_path / ".frob-release.json").exists()

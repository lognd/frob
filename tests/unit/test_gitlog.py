"""
Unit tests for frob.gitlog.git_log calling the library function directly
(not via CLI subprocess).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from frob.gitlog import git_log


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    # frob:secret-fake fabricated git identity for a test fixture repo
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=path, check=True)
    (path / "f.txt").write_text("one\n")
    subprocess.run(["git", "add", "f.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "feat: add first feature"], cwd=path, check=True
    )
    (path / "f.txt").write_text("two\n")
    subprocess.run(["git", "add", "f.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "chore: bump version"], cwd=path, check=True
    )


def test_git_log(tmp_path: Path) -> None:
    # frob:tests src/frob/gitlog/__init__.py::git_log kind="unit"
    _init_repo(tmp_path)

    result = git_log(tmp_path, granularity="full")

    types = {c.type for c in result.commits}
    assert "feat" in types
    assert "chore" in types

    user_result = git_log(tmp_path, granularity="user")
    assert all(c.type != "chore" for c in user_result.commits)


# frob:ticket T-0803
def test_git_log_kill_switch_refuses_without_spawning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # frob:tests src/frob/gitlog/__init__.py::git_log kind="unit"
    # T-0803: FROB_DISABLE_EXEC=1 must make git_log's underlying `git log`
    # spawn refuse (via guarded_subprocess_run) instead of bypassing the
    # T-0200/T-0778 exec guard -- proven with a spy on the real
    # `subprocess.run` so a spawn attempt would be observed, not assumed.
    _init_repo(tmp_path)
    monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
    spawned = False
    real_run = subprocess.run

    def _spy(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal spawned
        spawned = True
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy)
    result = git_log(tmp_path, granularity="full")
    assert not spawned
    assert list(result.commits) == []

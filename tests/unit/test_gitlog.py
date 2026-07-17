"""
Unit tests for frob.gitlog.git_log calling the library function directly
(not via CLI subprocess).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gitlog import git_log


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
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
